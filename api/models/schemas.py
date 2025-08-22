# The JSON schema for risk analysis
risk_schema = {
    "type": "object",
    "properties": {
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "A concise title for the risk."},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "The assessed severity of the risk."
                    },
                    "reason": {
                        "type": "string",
                        "description": "A brief explanation of why this is a risk."
                    },
                    "page": {
                        "type": "integer",
                        "description": "The page number where the risk was identified."
                    },
                    "mitigation": {
                        "type": "string",
                        "description": "A suggested action to mitigate the risk."
                    }
                },
                "required": ["title", "severity", "reason", "page", "mitigation"]
            }
        }
    },
    "required": ["risks"]
}