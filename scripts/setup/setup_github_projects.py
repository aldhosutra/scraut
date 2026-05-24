"""
scripts/setup/setup_github_projects.py
Create GitHub Projects v2 board with Scraut columns and custom fields.
Run once during initial setup after create_labels.py.
"""
import argparse
import logging
import os
import requests
from scripts.utils.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"
TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def gql(query: str, variables: dict = None) -> dict:
    resp = requests.post(GRAPHQL_URL,
                         json={"query": query, "variables": variables or {}},
                         headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def create_project(owner: str, title: str) -> str:
    """Create a new GitHub Projects v2. Returns project node ID."""
    owner_data = gql(
        'query($login: String!) { organization(login: $login) { id } }',
        {"login": owner}
    )
    owner_id = owner_data["organization"]["id"]

    result = gql(
        '''mutation($ownerId: ID!, $title: String!) {
          createProjectV2(input: {ownerId: $ownerId, title: $title}) {
            projectV2 { id number }
          }
        }''',
        {"ownerId": owner_id, "title": title}
    )
    project = result["createProjectV2"]["projectV2"]
    logger.info(f"Created project: {title} (#{project['number']})")
    return project["id"]


def add_status_field(project_id: str) -> None:
    """Update default Status field with Scraut columns."""
    fields_data = gql(
        '''query($id: ID!) {
          node(id: $id) {
            ... on ProjectV2 {
              fields(first: 20) {
                nodes {
                  ... on ProjectV2SingleSelectField { id name options { id name } }
                }
              }
            }
          }
        }''',
        {"id": project_id}
    )
    status_field = next(
        (f for f in fields_data["node"]["fields"]["nodes"]
         if f and f.get("name") == "Status"), None
    )

    if not status_field:
        logger.warning("Status field not found")
        return

    logger.info(f"Status field exists with {len(status_field['options'])} options")
    # Note: Modifying status options requires the Projects REST API
    # or manual setup in the GitHub UI. Document this for users.


def add_custom_field(project_id: str, name: str, field_type: str = "TEXT",
                     options: list = None) -> str:
    """Add a custom field to the project."""
    data_type = "TEXT" if field_type == "TEXT" else "NUMBER"
    result = gql(
        '''mutation($projectId: ID!, $name: String!, $dataType: ProjectV2CustomFieldType!) {
          createProjectV2Field(input: {
            projectId: $projectId
            name: $name
            dataType: $dataType
          }) { projectV2Field { ... on ProjectV2Field { id name } } }
        }''',
        {"projectId": project_id, "name": name,
         "dataType": data_type}
    )
    field_id = result["createProjectV2Field"]["projectV2Field"]["id"]
    logger.info(f"Created field: {name}")
    return field_id


def setup_project(owner: str, config: dict) -> int:
    """Create and configure the full Scraut GitHub Projects board."""
    title = config.get("portal", {}).get("title", "Scraut Board")
    project_id = create_project(owner, title)

    fields = [
        ("Agent", "TEXT"),
        ("SP Remaining", "NUMBER"),
        ("Blocker", "TEXT"),
        ("Sprint", "TEXT"),
        ("Last Activity", "TEXT"),
    ]
    for field_name, field_type in fields:
        add_custom_field(project_id, field_name, field_type)

    logger.info("\n✅ GitHub Projects board created!")
    logger.info("⚠️  Manual step required: Update Status field options in GitHub UI to:")
    logger.info("   Backlog | Ready | In Progress | Review | Testing | Done")
    logger.info("   (GraphQL API does not support option modification for single-select fields)")

    project_num_data = gql(
        'query($id: ID!) { node(id: $id) { ... on ProjectV2 { number } } }',
        {"id": project_id}
    )
    project_number = project_num_data["node"]["number"]
    logger.info(f"\nAdd this to scraut.yml:\n  portal:\n    project_number: {project_number}")
    return project_number


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup GitHub Projects board")
    parser.add_argument("owner", help="GitHub org or user login")
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    setup_project(args.owner, config)
