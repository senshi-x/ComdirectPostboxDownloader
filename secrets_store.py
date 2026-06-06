import os
import platform


ENV_SECRET_KEYS = {
    "pwd": "COMDIRECT_PWD",
    "clientSecret": "COMDIRECT_CLIENT_SECRET",
}

SECRET_KEYS = set(ENV_SECRET_KEYS.keys())
KEYRING_USERNAME = "comdirect"


class SecretStore:
    def __init__(self, project_dir: str, backend: str = "auto", namespace: str = "Banking/comdirect"):
        self.project_dir = project_dir
        self.namespace = namespace or "Banking/comdirect"
        self.backend = self.__resolve_backend(backend)
        self.env_file = os.path.join(project_dir, ".env")

    def get_secret(self, key: str) -> str | None:
        self.__validate_key(key)
        if self.backend == "keyring":
            return self.__get_keyring_secret(key)
        if self.backend == "env":
            return self.__get_env_secret(key)
        raise ValueError(f"Unsupported secret backend: {self.backend}")

    def set_secret(self, key: str, value: str) -> None:
        self.__validate_key(key)
        secret_value = value.strip()
        if self.backend == "keyring":
            self.__set_keyring_secret(key, secret_value)
            self.__print_store_result(key, secret_value)
            return
        if self.backend == "env":
            self.__set_env_secret(key, secret_value)
            self.__print_store_result(key, secret_value)
            return
        raise ValueError(f"Unsupported secret backend: {self.backend}")

    def __validate_key(self, key: str) -> None:
        if key not in SECRET_KEYS:
            raise ValueError(f"Unsupported secret key: {key}")

    def __print_store_result(self, key: str, value: str) -> None:
        print(f"Secret '{key}' gespeichert, Länge: {len(value)}")

    def __resolve_backend(self, backend: str) -> str:
        normalized_backend = (backend or "auto").strip().lower()
        if normalized_backend == "auto":
            if platform.system().lower() == "windows":
                return "keyring"
            return "env"
        if normalized_backend in ["keyring", "env"]:
            return normalized_backend
        raise ValueError("secretBackend must be one of: auto, keyring, env")

    def __get_keyring_secret(self, key: str) -> str | None:
        try:
            import keyring

            secret_value = keyring.get_password(self.__get_keyring_service(key), KEYRING_USERNAME)
            if secret_value is None:
                return self.__migrate_legacy_keyring_secret(key)
            return secret_value.strip()
        except Exception as error:
            raise RuntimeError(
                f"Secret '{key}' konnte nicht aus dem Backend '{self.backend}' gelesen werden: {type(error).__name__}: {error}"
            ) from error

    def __set_keyring_secret(self, key: str, value: str) -> None:
        try:
            import keyring

            keyring.set_password(self.__get_keyring_service(key), KEYRING_USERNAME, value)
            stored_value = keyring.get_password(self.__get_keyring_service(key), KEYRING_USERNAME)
            if stored_value is None:
                raise RuntimeError("Read-back nach dem Speichern lieferte keinen Wert.")
            if len(stored_value.strip()) != len(value):
                raise RuntimeError(
                    f"Read-back-Länge passt nicht: gespeichert={len(value)}, gelesen={len(stored_value.strip())}"
                )
        except Exception as error:
            raise RuntimeError(
                f"Secret '{key}' konnte nicht im Backend '{self.backend}' gespeichert werden: {type(error).__name__}: {error}"
            ) from error

    def __get_keyring_service(self, key: str) -> str:
        return f"{self.namespace.rstrip('/')}/{key}"

    def __migrate_legacy_keyring_secret(self, key: str) -> str | None:
        import keyring

        legacy_value = keyring.get_password(self.namespace, key)
        if legacy_value is None:
            return None

        secret_value = legacy_value.strip()
        keyring.set_password(self.__get_keyring_service(key), KEYRING_USERNAME, secret_value)
        print(
            f"Secret '{key}' aus altem keyring-Format gelesen: "
            f"service='{self.namespace}', username='{key}', Länge: {len(secret_value)}"
        )
        print(
            f"Secret '{key}' ins neue keyring-Format migriert: "
            f"service='{self.__get_keyring_service(key)}', username='{KEYRING_USERNAME}', Länge: {len(secret_value)}"
        )
        print(
            f"Hinweis: Alter keyring-Eintrag service='{self.namespace}', username='{key}' "
            "kann bei Bedarf manuell gelöscht werden."
        )
        return secret_value

    def __get_env_secret(self, key: str) -> str | None:
        env_key = ENV_SECRET_KEYS[key]
        values = self.__read_env_file()
        value = values.get(env_key)
        if value:
            return value.strip()
        env_value = os.environ.get(env_key)
        if env_value:
            return env_value.strip()
        return None

    def __set_env_secret(self, key: str, value: str) -> None:
        env_key = ENV_SECRET_KEYS[key]
        lines = []
        replaced = False

        if os.path.isfile(self.env_file):
            with open(self.env_file, "r", encoding="utf-8") as env_file:
                for line in env_file:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith("#") and "=" in stripped_line:
                        existing_key, _ = stripped_line.split("=", 1)
                        if existing_key.strip() == env_key:
                            lines.append(f"{env_key}={self.__escape_env_value(value)}\n")
                            replaced = True
                            continue
                    lines.append(line)

        if not replaced:
            if lines and lines[-1].strip():
                lines.append("\n")
            lines.append(f"{env_key}={self.__escape_env_value(value)}\n")

        with open(self.env_file, "w", encoding="utf-8") as env_file:
            env_file.writelines(lines)

    def __read_env_file(self) -> dict[str, str]:
        if not os.path.isfile(self.env_file):
            return {}

        values: dict[str, str] = {}
        with open(self.env_file, "r", encoding="utf-8") as env_file:
            for line in env_file:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
                    continue
                key, value = stripped_line.split("=", 1)
                values[key.strip()] = self.__unescape_env_value(value.strip())
        return values

    def __escape_env_value(self, value: str) -> str:
        if any(char in value for char in [" ", "\t", "\n", '"', "'"]):
            return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return value

    def __unescape_env_value(self, value: str) -> str:
        if len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if len(value) >= 2 and value[0] == value[-1] == "'":
            return value[1:-1]
        return value
