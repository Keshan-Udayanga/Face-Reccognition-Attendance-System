import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src import gemini_chat_service


class GeminiChatServiceTests(unittest.TestCase):
    @patch("src.gemini_chat_service.load_dotenv")
    @patch("src.gemini_chat_service._client_for_key")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"})
    def test_generates_reply_with_recent_conversation(self, client_for_key, _load_dotenv):
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=MagicMock(
                    return_value=SimpleNamespace(text="  Hello!  ")
                )
            )
        )
        client_for_key.return_value = client

        reply = gemini_chat_service.generate_chat_reply(
            [("user", "Hi"), ("model", "Hello"), ("user", "How are you?")]
        )

        self.assertEqual(reply, "Hello!")
        client_for_key.assert_called_once_with("test-key")
        self.assertEqual(
            client.models.generate_content.call_args.kwargs["model"],
            "test-model",
        )
        self.assertEqual(
            client.models.generate_content.call_args.kwargs["contents"],
            "User: Hi\nAssistant: Hello\nUser: How are you?",
        )
        self.assertEqual(
            client.models.generate_content.call_args.kwargs["config"].system_instruction,
            gemini_chat_service.SYSTEM_INSTRUCTION,
        )

    @patch("src.gemini_chat_service.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_requires_an_api_key(self, _load_dotenv):
        with self.assertRaises(gemini_chat_service.GeminiConfigurationError):
            gemini_chat_service.generate_chat_reply([("user", "Hello")])

    @patch("src.gemini_chat_service.load_dotenv")
    @patch("src.gemini_chat_service._client_for_key")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"})
    def test_creates_a_valid_data_request_plan(self, client_for_key, _load_dotenv):
        response_text = (
            '{"sources":["csv"],"intent":"attendance_summary",'
            '"employee_id":"7","employee_name":null,"date":"2026-11-19",'
            '"fields":["count"]}'
        )
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=MagicMock(
                    return_value=SimpleNamespace(text=response_text)
                )
            )
        )
        client_for_key.return_value = client

        plan = gemini_chat_service.generate_data_request_plan(
            [
                ("user", "How many attendance records does employee 7 have today?"),
                ("model", "Employee record: private information"),
            ]
        )

        self.assertEqual(
            plan,
            {
                "sources": ["csv"],
                "intent": "attendance_summary",
                "employee_id": "7",
                "employee_name": None,
                "date": "2026-11-19",
                "fields": ["count"],
            },
        )
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertEqual(config.system_instruction, gemini_chat_service.ROUTER_INSTRUCTION)
        contents = client.models.generate_content.call_args.kwargs["contents"]
        self.assertTrue(contents.startswith("Current date: "))
        self.assertTrue(
            contents.endswith(
                "User: How many attendance records does employee 7 have today?"
            )
        )

    @patch("src.gemini_chat_service.load_dotenv")
    @patch("src.gemini_chat_service._client_for_key")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_rejects_unsupported_data_sources(self, client_for_key, _load_dotenv):
        client_for_key.return_value = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=MagicMock(
                    return_value=SimpleNamespace(
                        text=(
                            '{"sources":["filesystem"],"intent":"general",'
                            '"employee_id":null,"employee_name":null,"date":null}'
                        )
                    )
                )
            )
        )

        with self.assertRaises(gemini_chat_service.GeminiResponseError):
            gemini_chat_service.generate_data_request_plan([("user", "Hello")])


if __name__ == "__main__":
    unittest.main()
