"""WebSocket tests against the real ASGI app (connecther.asgi.application): token middleware, URL routing,
the consumer, and core.notify.push through the InMemoryChannelLayer.

TransactionTestCase, not TestCase: channels' database_sync_to_async closes "old" DB connections, which
breaks TestCase's wrapping transaction, and on_commit hooks only fire for real with TransactionTestCase.
"""

from unittest import mock

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TransactionTestCase

from connecther.asgi import application
from core import notify
from core.consumers import CLOSE_UNAUTHORIZED
from core.models import Question, QuestionMatch
from core.tests.test_questions import FAST_HASHER, client_for, make_user

TIMEOUT = 3  # seconds to wait for a message that should arrive
UX_QUESTION = "How do I break into UX design without a design degree?"


async def connect(token=None, path="/ws/notifications/"):
    url = path if token is None else f"{path}?token={token}"
    comm = WebsocketCommunicator(application, url)
    connected, _ = await comm.connect(timeout=TIMEOUT)
    return comm, connected


@FAST_HASHER
class NotificationSocketTests(TransactionTestCase):
    def setUp(self):
        self.maya, self.maya_token = make_user("maya@t.com", "Maya Chen", "mentor")
        self.priya, self.priya_token = make_user("priya@t.com", "Priya Nair", "mentor")
        self.maria, self.maria_token = make_user("maria@t.com", "Maria Lopez", "mentee")

    def tearDown(self):
        # The in-memory layer is a process-wide singleton; don't leak groups or queued messages between tests.
        from asgiref.sync import async_to_sync

        async_to_sync(get_channel_layer().flush)()

    async def assert_rejected(self, comm):
        """The server accepts and then immediately closes with 4401 (see NotificationConsumer.connect)."""
        closed = await comm.receive_output(timeout=TIMEOUT)
        self.assertEqual(closed, {"type": "websocket.close", "code": CLOSE_UNAUTHORIZED})

    # --- auth ------------------------------------------------------------------------------------------

    async def test_no_token_is_rejected(self):
        comm, _ = await connect()
        await self.assert_rejected(comm)

    async def test_invalid_token_is_rejected(self):
        for bad in ["", "nope", "0" * 40]:
            with self.subTest(token=bad):
                comm, _ = await connect(bad)
                await self.assert_rejected(comm)

    async def test_inactive_user_is_rejected(self):
        await User.objects.filter(pk=self.maya.pk).aupdate(is_active=False)
        comm, _ = await connect(self.maya_token)
        await self.assert_rejected(comm)

    async def test_rejected_socket_gets_no_notifications(self):
        comm, _ = await connect("nope")
        await self.assert_rejected(comm)
        self.assertEqual(get_channel_layer().groups, {})

    async def test_valid_token_is_accepted(self):
        comm, connected = await connect(self.maya_token)
        self.assertTrue(connected)
        self.assertTrue(await comm.receive_nothing(timeout=0.3))  # still open, nothing sent
        await comm.disconnect()

    async def test_path_without_trailing_slash_also_works(self):
        comm, connected = await connect(self.maya_token, path="/ws/notifications")
        self.assertTrue(connected)
        self.assertTrue(await comm.receive_nothing(timeout=0.3))
        await comm.disconnect()

    # --- client messages -------------------------------------------------------------------------------

    async def test_ping_pong_and_other_messages_ignored(self):
        comm, _ = await connect(self.maya_token)
        await comm.send_json_to({"event": "ping"})
        self.assertEqual(await comm.receive_json_from(timeout=TIMEOUT), {"event": "pong"})
        await comm.send_json_to({"event": "hello"})
        await comm.send_to(text_data="not json {")
        await comm.send_json_to(["a", "list"])
        await comm.send_to(bytes_data=b"\x00\x01")
        self.assertTrue(await comm.receive_nothing(timeout=0.3))
        # Still alive after the junk.
        await comm.send_json_to({"event": "ping"})
        self.assertEqual(await comm.receive_json_from(timeout=TIMEOUT), {"event": "pong"})
        await comm.disconnect()

    # --- push ------------------------------------------------------------------------------------------

    async def test_push_delivers_payload(self):
        comm, _ = await connect(self.maya_token)
        payload = {"event": "new_question", "match_id": 1, "question_id": 2, "question": "Q?", "reason": "R",
                   "mentee_name": "Maria L."}
        sent = await sync_to_async(notify.push)(self.maya.id, payload)
        self.assertTrue(sent)
        self.assertEqual(await comm.receive_json_from(timeout=TIMEOUT), payload)
        await comm.disconnect()

    async def test_push_only_reaches_that_user_but_all_their_sockets(self):
        maya_tab1, _ = await connect(self.maya_token)
        maya_tab2, _ = await connect(self.maya_token)
        priya, _ = await connect(self.priya_token)
        await sync_to_async(notify.push)(self.maya.id, {"event": "x"})
        self.assertEqual(await maya_tab1.receive_json_from(timeout=TIMEOUT), {"event": "x"})
        self.assertEqual(await maya_tab2.receive_json_from(timeout=TIMEOUT), {"event": "x"})
        self.assertTrue(await priya.receive_nothing(timeout=0.3))
        for comm in (maya_tab1, maya_tab2, priya):
            await comm.disconnect()

    async def test_disconnect_leaves_group(self):
        comm, _ = await connect(self.maya_token)
        self.assertIn(f"user_{self.maya.id}", get_channel_layer().groups)
        await comm.disconnect()
        self.assertNotIn(f"user_{self.maya.id}", get_channel_layer().groups)

    async def test_push_with_nobody_connected_is_fine(self):
        self.assertTrue(await sync_to_async(notify.push)(self.maya.id, {"event": "x"}))

    async def test_push_never_raises(self):
        with mock.patch("core.notify.get_channel_layer", side_effect=RuntimeError("layer down")):
            with self.assertLogs("core.notify", level="ERROR"):
                sent = await sync_to_async(notify.push)(self.maya.id, {"event": "x"})
        self.assertFalse(sent)

    # --- full flows through the REST API ---------------------------------------------------------------

    def _ask_as_maria(self):
        fake = [{"mentor_id": self.maya.id, "reason": "Switched into UX from teaching"},
                {"mentor_id": self.priya.id, "reason": "Data background"}]
        with mock.patch("core.views.matching.match_mentors", return_value=fake):
            return client_for(self.maria_token).post("/api/questions/", {"text": UX_QUESTION}, format="json")

    async def test_asking_a_question_notifies_matched_mentors(self):
        maya, _ = await connect(self.maya_token)
        priya, _ = await connect(self.priya_token)
        maria, _ = await connect(self.maria_token)

        res = await sync_to_async(self._ask_as_maria)()
        self.assertEqual(res.status_code, 201)
        question_id = res.data["id"]
        maya_match, priya_match = res.data["matches"]

        self.assertEqual(
            await maya.receive_json_from(timeout=TIMEOUT),
            {
                "event": "new_question",
                "match_id": maya_match["match_id"],
                "question_id": question_id,
                "question": UX_QUESTION,
                "reason": "Switched into UX from teaching",
                "mentee_name": "Maria L.",
            },
        )
        priya_event = await priya.receive_json_from(timeout=TIMEOUT)
        self.assertEqual(priya_event["match_id"], priya_match["match_id"])
        self.assertEqual(priya_event["reason"], "Data background")
        self.assertTrue(await maria.receive_nothing(timeout=0.3))  # the asker gets nothing
        for comm in (maya, priya, maria):
            await comm.disconnect()

    def _answer_as_maya(self, text):
        question = Question.objects.create(mentee=self.maria, text=UX_QUESTION)
        match = QuestionMatch.objects.create(question=question, mentor=self.maya, reason="UX", rank=1)
        res = client_for(self.maya_token).post(f"/api/matches/{match.id}/answer/", {"text": text}, format="json")
        return res, match

    async def test_answering_notifies_the_mentee(self):
        maria, _ = await connect(self.maria_token)
        maya, _ = await connect(self.maya_token)

        res, match = await sync_to_async(self._answer_as_maya)("  Start with 3 case studies.  ")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(
            await maria.receive_json_from(timeout=TIMEOUT),
            {
                "event": "new_answer",
                "question_id": match.question_id,
                "match_id": match.id,
                "mentor_name": "Maya Chen",
                "text": "Start with 3 case studies.",
            },
        )
        self.assertTrue(await maya.receive_nothing(timeout=0.3))
        for comm in (maria, maya):
            await comm.disconnect()

    async def test_request_still_succeeds_when_push_fails(self):
        maya, _ = await connect(self.maya_token)
        with mock.patch("core.notify.get_channel_layer", side_effect=RuntimeError("layer down")):
            with self.assertLogs("core.notify", level="ERROR"):
                res = await sync_to_async(self._ask_as_maria)()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data["matches"]), 2)
        self.assertTrue(await maya.receive_nothing(timeout=0.3))
        await maya.disconnect()
