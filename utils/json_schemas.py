from constants import Encoding, Resolution, ReleaseGroupEpisodeNumberingAffinity, ReleaseTitlePart

RELEASE_GROUPS_JSON_SCHEMA = {
    "type": "object",
    "required": ["release_groups"],
    "additionalProperties": True,
    "properties": {
        "release_groups": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": [
                    "submitter",
                    "unique_filter",
                    "regex",
                    "default_encoding",
                    "default_resolution",
                    "default_language_code",
                    "episode_numbering_affinity",
                    "batch_keyword"
                ],
                "properties": {
                    "submitter": {"type": "string"},
                    "unique_filter": {
                        "type": "object",
                        "required": ["startswith"],
                        "properties": {
                            "startswith": {"type": "string"},
                        },
                        "additionalProperties": True,
                    },
                    "regex": {
                        "type": "array", "items":
                            {"type": "object",
                             "required": ["pattern", "required_pattern_groups"],
                             "properties": {
                                 "pattern": {"type": "string"},
                                 "required_pattern_groups": {"type": "array",
                                                             "items": {"type": "string",
                                                                       "enum": ReleaseTitlePart.as_list()}},
                             },
                             "additionalProperties": True, }
                    },

                    "default_encoding": {"type": "string", "enum": Encoding.as_list()},
                    "default_resolution": {"type": "string", "enum": Resolution.as_list()},
                    "default_language_code": {"type": "string"},
                    "batch_keyword": {"type": "string"},
                    "episode_numbering_affinity": {"type": "string",
                                                   "enum": ReleaseGroupEpisodeNumberingAffinity.as_list()},
                },
                "additionalProperties": True,
            },
        },
    },
}

CONFIG_JSON_SCHEMA = {
    "type": "object",
    "required": ["port", "log_level", "db", "credentials", "networking"],
    "additionalProperties": True,
    "properties": {
        "port": {"type": "integer"},
        "log_level": {"type": "string"},
        "db": {
            "type": "object",
            "required": ["host", "port", "name", "user", "password"],
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer"},
                "name": {"type": "string"},
                "user": {"type": "string"},
                "password": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "credentials": {
            "type": "object",
            "required": ["username", "password", "jwt_secret"],
            "properties": {
                "username": {"type": "string"},
                "password": {"type": "string"},
                "jwt_secret": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "networking": {
            "type": "object",
            "required": ["allow_all_origins", "proxy_external_images"],
            "properties": {
                "allow_all_origins": {"type": "boolean"},
                "proxy_external_images": {"type": "boolean"},
            },
            "additionalProperties": True,
        },
    },
}
