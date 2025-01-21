import os
import yaml
import requests
from requests.auth import HTTPBasicAuth
import click
import json

# Default path to the YAML configuration file
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.planningcenter_toolkit/pat.yaml")

def load_authentication(config_path):
    """
    Load authentication credentials from the specified YAML file.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}. Please create it.")

    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    client_id = config.get("client_id")
    client_secret = config.get("client_secret")

    if not client_id or not client_secret:
        raise ValueError("The YAML file must contain both 'client_id' and 'client_secret'.")

    return client_id, client_secret


def fetch_people(client_id, client_secret, limit):
    """
    Fetch people data from the Planning Center API.
    """
    auth = HTTPBasicAuth(client_id, client_secret)
    params = {
        "include": "phone_numbers,emails,addresses,households",
        "per_page": 100  # Fetch up to 100 people per page
    }

    people_list = []
    next_page = "https://api.planningcenteronline.com/people/v2/people"

    while next_page:
        response = requests.get(next_page, auth=auth, params=params)
        response.raise_for_status()
        data = response.json()

        # Process each person in the current page
        for person in data["data"]:
            if len(people_list) >= limit:
                break  # Stop adding people once we've reached the limit

            attributes = person["attributes"]
            person_info = {
                "id": person["id"],
                "first_name": attributes.get("first_name"),
                "last_name": attributes.get("last_name"),
                "nickname": attributes.get("nickname"),
                "birthday": attributes.get("birthdate"),
                "anniversary": attributes.get("anniversary"),
                "gender": attributes.get("gender"),
                "marital_status": attributes.get("marital_status"),
                "child": attributes.get("child"),
                "avatar": attributes.get("avatar"),
                "status": attributes.get("status"),
                "inactivated_at": attributes.get("inactivated_at"),
                "inactive_reason": attributes.get("inactive_reason"),
                "membership": attributes.get("membership"),
                "created_at": attributes.get("created_at"),
                "updated_at": attributes.get("updated_at"),
                "graduation_year": attributes.get("graduation_year"),
                "medical_notes": attributes.get("medical_notes"),
                "school_type": attributes.get("school_type"),
                "login_identifier": attributes.get("login_identifier"),
                # Household count (default to 0 if not found)
                "household_count": 0,
                # Address components
                "home_street": None,
                "home_city": None,
                "home_state": None,
                "home_zip": None,
                "work_street": None,
                "work_city": None,
                "work_state": None,
                "work_zip": None,
                # Contact details
                "phone_numbers": [],
                "emails": []
            }

            included_data = {item["id"]: item for item in data.get("included", [])}
            
            for rel_type, rel_data in person.get("relationships", {}).items():
                if rel_type == "phone_numbers":
                    for phone_id in rel_data["data"]:
                        phone = included_data.get(phone_id["id"])
                        if phone:
                            person_info["phone_numbers"].append(phone["attributes"]["number"])
                
                elif rel_type == "emails":
                    for email_id in rel_data["data"]:
                        email = included_data.get(email_id["id"])
                        if email:
                            person_info["emails"].append(email["attributes"]["address"])

                elif rel_type == "addresses":
                    for address_id in rel_data["data"]:
                        address = included_data.get(address_id["id"])
                        if address:
                            address_type = address["attributes"]["location"]
                            if address_type == "Home":
                                person_info["home_street"] = address["attributes"].get("street")
                                person_info["home_city"] = address["attributes"].get("city")
                                person_info["home_state"] = address["attributes"].get("state")
                                person_info["home_zip"] = address["attributes"].get("zip")
                            elif address_type == "Work":
                                person_info["work_street"] = address["attributes"].get("street")
                                person_info["work_city"] = address["attributes"].get("city")
                                person_info["work_state"] = address["attributes"].get("state")
                                person_info["work_zip"] = address["attributes"].get("zip")

                elif rel_type == "households":
                    for household in rel_data["data"]:
                        household_id = household["id"]
                        household_data = included_data.get(household_id)
                        if household_data and household_data["type"] == "Household":
                            member_count = household_data["attributes"].get("member_count", 0)
                            person_info["household_count"] += member_count

            people_list.append(person_info)

        # Stop fetching new pages if we've reached the limit
        if len(people_list) >= limit:
            break

        next_page = data.get("links", {}).get("next")

    return people_list



@click.group()
def cli():
    """
    A CLI tool for interacting with the Planning Center API.
    """
    pass


@cli.group()
def get():
    """
    Group of commands to fetch data from the Planning Center API.
    """
    pass


@get.command()
@click.option(
    "--limit",
    default=10,
    help="Limit the number of results returned (default is 10)."
)
@click.option(
    "--config",
    default=DEFAULT_CONFIG_PATH,
    help="Path to the configuration YAML file."
)
def people(limit, config):
    """
    Fetch and display people data from the Planning Center API.
    """
    try:
        # Load authentication credentials
        client_id, client_secret = load_authentication(config)

        # Fetch people data with the specified limit
        people = fetch_people(client_id, client_secret, limit)

        # Define headers for tabular output
        headers = [
            "ID", 
            "First Name", 
            "Last Name", 
            "Nickname",
            "Birthday", 
            "Anniversary", 
            "Gender", 
            "Marital Status", 
            "Child", 
            "Avatar URL", 
            "Status",
            "Inactivated At",
            "Inactive Reason",
            "Membership",
            "Created At",
            "Updated At",
            # Household count and addresses
            "Household Count",
            # Home Address components
            "Home Street", 
            "Home City", 
            "Home State", 
            "Home Zip",
            # Work Address components
            "Work Street", 
            "Work City", 
            "Work State", 
            "Work Zip",
            # Contact details
            "Phone Numbers", 
            "Emails"
        ]

        # Print headers
        print("\t".join(headers))

        # Print each person's information in tab-delimited format
        for person in people:
            row = [
                person["id"],
                person["first_name"] or "",
                person["last_name"] or "",
                person["nickname"] or "",
                person["birthday"] or "",
                person["anniversary"] or "",
                person["gender"] or "",
                person["marital_status"] or "",
                str(person["child"]) if person["child"] is not None else "",
                person["avatar"] or "",
                person["status"] or "",
                person["inactivated_at"] or "",
                person["inactive_reason"] or "",
                person["membership"] or "",
                person["created_at"] or "",
                person["updated_at"] or "",
                str(person['household_count']),
                # Home Address components
                person["home_street"] or "",
                person["home_city"] or "",
                person["home_state"] or "",
                person["home_zip"] or "",
                # Work Address components
                person["work_street"] or "",
                person["work_city"] or "",
                person["work_state"] or "",
                person["work_zip"] or "",
                ", ".join(person["phone_numbers"]),
                ", ".join(person["emails"])
            ]
            print("\t".join(row))

    except FileNotFoundError as e:
        print(f"Error: {e}. Please ensure the configuration file exists at {config}.")
    except ValueError as e:
        print(f"Error: {e}. Please ensure the configuration file contains valid credentials.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Planning Center API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def create_default_config():
    """
    Create a default configuration YAML file.
    """
    # Define default configuration data
    default_config = {
        "client_id": "your_client_id_here",
        "client_secret": "your_client_secret_here"
    }

    # Ensure the directory exists
    os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)

    # Write the default configuration to the YAML file
    with open(DEFAULT_CONFIG_PATH, "w") as file:
        yaml.dump(default_config, file)

    print(f"Default configuration created at {DEFAULT_CONFIG_PATH}. Please update it with your credentials.")

@cli.command()
@click.option(
    "--config",
    default=DEFAULT_CONFIG_PATH,
    help="Path to the configuration YAML file."
)
def init(config):
    """
    Initialize the configuration file for the Planning Center Toolkit.
    """
    create_default_config(config)


def fetch_teams(client_id, client_secret, limit):
   """
   Fetch all teams from the Planning Center API with an optional limit.
   """
   auth = HTTPBasicAuth(client_id, client_secret)
   url = "https://api.planningcenteronline.com/services/v2/teams"  # Update this URL based on your needs
   response = requests.get(url, auth=auth)
   response.raise_for_status()
   data = response.json()

   # Limit the number of teams returned based on user input
   return [{"id": team["id"], "name": team["attributes"]["name"], "positions": team["attributes"].get("positions", [])} for team in data["data"]][:limit]

def fetch_people_in_team(client_id, client_secret, team_id):
   """
   Fetch all people associated with a specific team from the Planning Center API.
   """
   auth = HTTPBasicAuth(client_id, client_secret)
   url = f"https://api.planningcenteronline.com/services/v2/teams/{team_id}/people"  # Update this URL based on your needs
   response = requests.get(url, auth=auth)
   response.raise_for_status()
   data = response.json()

   return [
       {
           "id": person["id"],
           "first_name": person["attributes"].get("first_name"),
           "last_name": person["attributes"].get("last_name"),
           "emails": [email["address"] for email in person.get("emails", [])],
           "phone_numbers": [phone["number"] for phone in person.get("phone_numbers", [])]
       }
       for person in data["data"]
   ]


@get.command()
@click.option(
    "--limit",
    default=10,
    help="Limit the number of teams returned (default is 10)."
)
@click.option(
    "--config",
    default=DEFAULT_CONFIG_PATH,
    help="Path to the configuration YAML file."
)
def teams(limit, config):
    """
    Fetch and display all teams and their associated persons from the Planning Center API.
    """
    try:
        client_id, client_secret = load_authentication(config)
        
        # Fetch teams with limit
        teams_list = fetch_teams(client_id, client_secret, limit)

        # Print headers for teams
        team_headers = ["Team ID", "Team Name", "Positions", "Person ID", "First Name", "Last Name", "Emails", "Phone Numbers"]
        print("\t".join(team_headers))

        for team in teams_list:
            # Fetch people associated with each team
            people_in_team = fetch_people_in_team(client_id, client_secret, team['id'])
            for person in people_in_team:
                print("\t".join([
                    str(team['id']),
                    team['name'],
                    ", ".join(team['positions']),
                    str(person['id']),
                    person['first_name'] or "",
                    person['last_name'] or "",
                    ", ".join(person['emails']),
                    ", ".join(person['phone_numbers'])
                ]))

            # If you want to print team info even if there are no people,
            # you can add a check here to handle that case.

    except Exception as e:
        print(f"Error fetching teams: {e}")

def get_paginated_results(url, auth):
    results = []
    while url:
        response = requests.get(url, auth=auth)
        if response.status_code != 200:
            print(f"Error fetching data: Status code {response.status_code}")
            break
        data = response.json()
        results.extend(data["data"])
        url = data["links"].get("next")
    return results

@cli.group()
def clear():
    """
    Group of commands to clear data from the Planning Center API.
    """
    pass

@clear.command()
@click.option(
    "--config",
    default=DEFAULT_CONFIG_PATH,
    help="Path to the configuration YAML file."
)
@click.option(
    "--service-type-name",
    default="English Worship Service",
    help="Name of service type"
)
@click.option(
    "--team-position-name",
    help="Name of team position to clear."
)
def team_position(config, service_type_name, team_position_name):
    # auth
    client_id, client_secret = load_authentication(config)
    base_url = "https://api.planningcenteronline.com/services/v2"
    auth = HTTPBasicAuth(client_id, client_secret)

    # Step 1: Get the service type ID
    service_types_url = f"{base_url}/service_types"
    service_types = get_paginated_results(service_types_url, auth)
    service_type_id = next((st["id"] for st in service_types if st["attributes"]["name"] == service_type_name), None)

    if not service_type_id:
        print(f"Service type '{service_type_name}' not found.")
        return

    # Step 2: Get the team position ID
    team_positions_url = f"{base_url}/service_types/{service_type_id}/team_positions"
    team_positions = get_paginated_results(team_positions_url, auth)
    team_position_id = next((tp["id"] for tp in team_positions if tp["attributes"]["name"] == team_position_name), None)

    if not team_position_id:
        print(f"Team position '{team_position_name}' not found in service type '{service_type_name}'.")
        return

    # Step 3: Get person team position assignments
    assignments_url = f"{base_url}/service_types/{service_type_id}/team_positions/{team_position_id}/person_team_position_assignments"
    assignments = get_paginated_results(assignments_url, auth)

    # Step 4: Remove each assignment
    for assignment in assignments:
        assignment_id = assignment["id"]
        delete_url = f"{base_url}/service_types/{service_type_id}/team_positions/{team_position_id}/person_team_position_assignments/{assignment_id}"
        delete_response = requests.delete(delete_url, auth=auth)

        if delete_response.status_code == 204:
            print(f"Successfully removed assignment {assignment_id} from {team_position_name} in {service_type_name}")
        else:
            print(f"Failed to remove assignment {assignment_id}. Status code: {delete_response.status_code}")

    print(f"All assignments have been removed from {team_position_name} in {service_type_name}.")


if __name__ == "__main__":
    cli()
