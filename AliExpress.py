from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
from rich import print

def fetch_package_updates(packages, output_file="packages_updates.json", show_only_updates=True):
    base_url = "http://www.rapidposte.poste.tn/fr/Item_Events.asp?ItemId="
    results = []
    total_packages = len(packages)
    found_updates = 0
    in_tunisia = 0
    packages_in_tunisia = {"Ghazala": [], "Ariana": [], "Tunis": []}

    print(f"{total_packages} packages to check found\n")

    for idx, pkg in enumerate(packages, start=1):
        pkg_number_original = pkg["package_number"]
        pkg_items = pkg.get("package orders", [])

        print(f"Checking package n°{idx} : {pkg_number_original}")

        pkg_numbers_to_try = [pkg_number_original]
        if "/" in pkg_number_original:
            pkg_numbers_to_try = pkg_number_original.split('/')

        soup = None
        pkg_number = None

        for attempt in pkg_numbers_to_try:
            url = base_url + attempt
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                temp_soup = BeautifulSoup(response.text, "html.parser")
                if temp_soup.find("table", {"id": "200"}):
                    soup = temp_soup
                    pkg_number = attempt
                    print(f"  → Found updates with {pkg_number}")
                    break
                else:
                    print(f"  → No updates for {attempt}")
            except requests.RequestException as e:
                print(f"  ⚠ Error fetching {attempt}: {e}")
        
        if not soup:
            print("  → no package update\n")
            results.append({
                "package_number": pkg_number_original,
                "orders": pkg_items,
                "updates": "no package update"
            })
            continue

        table = soup.find("table", {"id": "200"})

        print("  → package updates found\n")
        found_updates += 1

        updates = []
        rows = table.find_all("tr")[2:]  # skip header rows

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            date = cols[0].get_text(strip=True)
            pays = cols[1].get_text(strip=True)
            lieu = cols[2].get_text(strip=True)
            event = cols[3].get_text(strip=True)

            updates.append({
                "Date": date,
                "Pays": pays,
                "Lieu": lieu,
                "Type d'événement": event
            })

        # Determine location priority: Ghazala > Ariana > Tunis
        location = ""
        if any("ghazala" in u["Lieu"].lower() for u in updates):
            location = "Ghazala"
            in_tunisia += 1
            packages_in_tunisia[location].append(pkg_items)
        elif any("ariana" in u["Lieu"].lower() for u in updates):
            location = "Ariana"
            in_tunisia += 1
            packages_in_tunisia[location].append(pkg_items)
        elif any("tunis" in u["Lieu"].lower() for u in updates):
            location = "Tunis"
            in_tunisia += 1
            packages_in_tunisia[location].append(pkg_items)
        else:
            location = "on the way"

        results.append({
            "package_number": pkg_number,
            "orders": pkg_items,
            "n° of updates": len(updates),
            "location": location,
            "days since first update": (
            (datetime.now() - datetime.strptime(updates[0]["Date"], "%d/%m/%Y %H:%M:%S")).days
            if updates else 0
            ),
            "days since last update": (
            (datetime.now() - datetime.strptime(updates[-1]["Date"], "%d/%m/%Y %H:%M:%S")).days
            if updates else 0
            ),
            "updates": updates
        })

    # Print summary

    # Save to JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    if show_only_updates:
        results = [res for res in results if res["updates"] != "no package update"]

    # save all the prints below to a log file
    with open("update_log.txt", "w", encoding="utf-8") as log_file:
        log_file.write(f"Summary: \n - {found_updates}/{total_packages} packages updates found")
        log_file.write(f" - {in_tunisia}/{found_updates} packages are in Tunisia\n")
        log_file.write("Packages in Tunisia by location:\n")
        for loc, pkgs in packages_in_tunisia.items():
            log_file.write(f" - {loc}: {len(pkgs)} packages\n")
            for p in pkgs:
                log_file.write(f"    • Orders: {p}\n")

    return results

with open("package_list.json", "r", encoding="utf-8") as f:
    packages_list = json.load(f)

if __name__ == "__main__":
    fetch_package_updates(packages_list, show_only_updates=True)
