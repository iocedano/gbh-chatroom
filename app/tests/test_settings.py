import unittest

from pydantic import ValidationError

from infra.settings import Settings, get_settings


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()

    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_accepts_default_secret_in_development(self) -> None:
        settings = Settings(app_env="development", jwt_secret_key="change-me-in-development")
        self.assertEqual(settings.jwt_secret_key.get_secret_value(), "change-me-in-development")

    def test_rejects_default_secret_in_production(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(app_env="production", jwt_secret_key="change-me-in-development")

    def test_parses_comma_separated_cors_origins(self) -> None:
        settings = Settings(cors_origins="https://app.example.com, https://admin.example.com")
        self.assertEqual(
            settings.cors_origins,
            ["https://app.example.com", "https://admin.example.com"],
        )

    def test_parses_json_cors_origins(self) -> None:
        settings = Settings(cors_origins='["https://app.example.com", "https://admin.example.com"]')
        self.assertEqual(
            settings.cors_origins,
            ["https://app.example.com", "https://admin.example.com"],
        )


if __name__ == "__main__":
    unittest.main()
