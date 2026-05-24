"""
scripts/github/projects.py
GitHub Projects v2 GraphQL API wrapper.
Used by the visibility engine to sync board state from text artifacts.
"""
import os
import requests
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"


def graphql_request(query: str, variables: dict = None,
                    token: Optional[str] = None) -> dict:
    """Execute a GitHub GraphQL query."""
    token = token or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(GRAPHQL_URL, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def get_project_id(owner: str, project_number: int, token: Optional[str] = None) -> str:
    """Get the node ID of a GitHub Project."""
    query = """
    query($owner: String!, $number: Int!) {
      organization(login: $owner) {
        projectV2(number: $number) { id }
      }
    }
    """
    data = graphql_request(query, {"owner": owner, "number": project_number}, token)
    return data["organization"]["projectV2"]["id"]


def get_project_items(project_id: str, token: Optional[str] = None) -> list[dict]:
    """Get all items in a GitHub Project."""
    query = """
    query($projectId: ID!, $cursor: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              content {
                ... on Issue {
                  number title state
                  assignees(first: 5) { nodes { login } }
                  labels(first: 10) { nodes { name } }
                }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2SingleSelectField { name } }
                  }
                  ... on ProjectV2ItemFieldTextValue {
                    text
                    field { ... on ProjectV2Field { name } }
                  }
                  ... on ProjectV2ItemFieldNumberValue {
                    number
                    field { ... on ProjectV2Field { name } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    items = []
    cursor = None
    while True:
        data = graphql_request(query, {"projectId": project_id, "cursor": cursor}, token)
        page = data["node"]["items"]
        items.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return items


def update_item_status(project_id: str, item_id: str, status_field_id: str,
                       option_id: str, token: Optional[str] = None) -> None:
    """Move a project item to a different status column."""
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: { singleSelectOptionId: $optionId }
      }) { projectV2Item { id } }
    }
    """
    graphql_request(mutation, {
        "projectId": project_id, "itemId": item_id,
        "fieldId": status_field_id, "optionId": option_id
    }, token)


def update_item_text_field(project_id: str, item_id: str, field_id: str,
                           value: str, token: Optional[str] = None) -> None:
    """Update a text custom field on a project item."""
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: { text: $value }
      }) { projectV2Item { id } }
    }
    """
    graphql_request(mutation, {
        "projectId": project_id, "itemId": item_id,
        "fieldId": field_id, "value": value
    }, token)


def get_field_ids(project_id: str, token: Optional[str] = None) -> dict[str, dict]:
    """Get all field IDs and option IDs for a project."""
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 30) {
            nodes {
              ... on ProjectV2Field { id name }
              ... on ProjectV2SingleSelectField {
                id name
                options { id name }
              }
            }
          }
        }
      }
    }
    """
    data = graphql_request(query, {"projectId": project_id}, token)
    fields = {}
    for field in data["node"]["fields"]["nodes"]:
        if not field:
            continue
        name = field.get("name")
        fields[name] = {
            "id": field["id"],
            "options": {opt["name"]: opt["id"]
                        for opt in field.get("options", [])}
        }
    return fields
