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


if __name__ == "__main__":
    unittest.main()
