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
    arrived = 0

    print(f"{total_packages} packages to check found\n")

    for idx, pkg in enumerate(packages, start=1):
        pkg_number = pkg["package_number"]
        pkg_items = pkg.get("package orders", [])

        print(f"Checking package n°{idx} : {pkg_number}")

        url = base_url + pkg_number
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"  ⚠ Error fetching {pkg_number}: {e}")
            results.append({
                "package_number": pkg_number,
                "orders": pkg_items,
                "updates": "error fetching page"
            })
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"id": "200"})

        if not table:
            print("  → no package update\n")
            results.append({
                "package_number": pkg_number,
                "orders": pkg_items,
                "updates": "no package update"
            })
            continue

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
            arrived += 1
        elif any("ariana" in u["Lieu"].lower() for u in updates):
            location = "Ariana"
            arrived += 1
        elif any("tunis" in u["Lieu"].lower() for u in updates):
            location = "Tunis"
            arrived += 1
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

    print("\n","-"*50,"\n")
    print(f"Results saved to {output_file}\n")
    print(json.dumps(results, indent=4, ensure_ascii=False))
    print("\n","-"*50,"\n")
    print(f"Summary: \n - {found_updates}/{total_packages} packages updates found")
    print(f" - {arrived}/{found_updates} packages are in Tunisia\n")

    return results

with open("package_list.json", "r", encoding="utf-8") as f:
    packages_list = json.load(f)

if __name__ == "__main__":
    fetch_package_updates(packages_list, show_only_updates=True)
