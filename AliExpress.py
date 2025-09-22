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
    on_the_way = 0
    packages_in_tunisia = {"Ghazala": [], "Ariana": [], "Tunis": []}
    packages_on_the_way = []

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
                "n°": idx,
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
        last_update_date = updates[-1]["Date"] if updates else None
        is_today = datetime.now().strftime("%d/%m/%Y") == datetime.strptime(last_update_date, "%d/%m/%Y %H:%M:%S").strftime("%d/%m/%Y") if last_update_date else False
        if any("Livré" in u["Type d'événement"] for u in updates):
            delivered = True
        else:
            delivered = False
        if any("ghazala" in u["Lieu"].lower() for u in updates):
            location = "Ghazala"
            in_tunisia += 1
            # change the the tuple to a dict for better readability
            packages_in_tunisia[location].append({
                "package_number": pkg_number,
                "orders": pkg_items,
                "last_update_date": last_update_date,
                "delivered": delivered,
                "is_today": is_today
            })
        elif any("ariana" in u["Lieu"].lower() for u in updates):
            location = "Ariana"
            in_tunisia += 1
            packages_in_tunisia[location].append({
                "package_number": pkg_number,
                "orders": pkg_items,
                "last_update_date": last_update_date,
                "delivered": delivered,
                "is_today": is_today
            })
        elif any("tunis" in u["Lieu"].lower() for u in updates):
            location = "Tunis"
            in_tunisia += 1
            packages_in_tunisia[location].append({
                "package_number": pkg_number,
                "orders": pkg_items,
                "last_update_date": last_update_date,
                "delivered": delivered,
                "is_today": is_today
            })
        else:
            location = "on the way"
            on_the_way += 1
            packages_on_the_way.append({
                "package_number": pkg_number,
                "orders": pkg_items,
                "last_update_date": last_update_date,
                "is_today": is_today
            })

        results.append({
            "n°": idx,
            "package_number": pkg_number,
            "orders": pkg_items,
            "n° of updates": len(updates),
            "location": location,
            "delivered": delivered,
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
        with_update = [res for res in results if res["updates"] != "no package update"]
        no_update = [res for res in results if res["updates"] == "no package update"]

    # Print results
    for res in with_update:
        print(json.dumps(res, indent=4, ensure_ascii=False))
        print()

    # print & save all the logs below to a log file at the same time
    log_output = []
    separator = "-" * 80
    order_cut = 30
    log_output.append(f"Summary: \n - {found_updates}/{total_packages} packages updates found")
    log_output.append(f" - {in_tunisia}/{found_updates} packages are in Tunisia\n")
    log_output.append("Packages in Tunisia by location:")
    for loc, pkgs in packages_in_tunisia.items():
        log_output.append(f"\n - {loc}: {len(pkgs)} packages")
        if pkgs:
            log_output.append(separator)
            # first_order = None
        for p in pkgs:
            orders = f"\t{p['package_number']}"
            first_order = p['orders'][0][:order_cut]+"..."
            orders += f"\t|\t{first_order.ljust(order_cut+3)}"
            orders += f"\t|\t{p['last_update_date']}"
            if p['delivered']:
                orders += f"\t|\t✅ Delivered ✅"
            if p['is_today']:
                orders += f"\t|\t✨ Today ✨"
            if len(p['orders']) > 1:
                for o in p['orders'][1:]:
                    orders += f"\n\t\t\t\t\t\t{o[:order_cut]+"..."}"
            log_output.append(orders)
            log_output.append(separator)
            
    log_output.append(f"\n - On the way: {on_the_way} packages")
    if packages_on_the_way:
        log_output.append(separator)
    for p in packages_on_the_way:
        orders = f"\t{p['package_number']}"
        first_order = p['orders'][0][:order_cut]+"..."
        orders += f"\t|\t{first_order.ljust(order_cut+3)}"
        orders += f"\t|\t{p['last_update_date']}"
        if p['is_today']:
            orders += f"\t|\t✨ Today ✨"
        if len(p['orders']) > 1:
            for o in p['orders'][1:]:
                orders += f"\n\t\t\t\t\t\t{o[:order_cut]+"..."}"
        log_output.append(orders)
        log_output.append(separator) 
        
    log_output.append(f"\n - No updates: {len(no_update)} packages")
    if no_update:
        log_output.append(separator)
    for res in no_update:
        log_output.append(f"\t{res['orders'][0][:order_cut]+"..."}\t|\t{res['package_number']}")

    print("\n".join(log_output))
    with open("update_log.txt", "w", encoding="utf-8") as log_file:
        log_file.write("\n".join(log_output))

    return with_update, no_update


with open("package_list.json", "r", encoding="utf-8") as f:
    packages_list = json.load(f)

if __name__ == "__main__":
    fetch_package_updates(packages_list, show_only_updates=True)
