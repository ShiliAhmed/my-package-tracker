from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import logging
from rich import print

logger = logging.getLogger(__name__)


def fetch_package_updates(packages, output_file="packages_updates.json", show_only_updates=True):
    base_url = "http://www.rapidposte.poste.tn/fr/Item_Events.asp?ItemId="
    results = []
    total_packages = len(packages)
    found_updates = 0
    in_tunisia = 0
    on_the_way = 0
    show_delivered = False
    packages_in_tunisia = {"Ghazala": [], "Ariana": [], "Tunis": []}
    packages_in_tunisia_not_delivered = {"Ghazala": [], "Ariana": [], "Tunis": []}
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
                logger.info(f"Fetching URL: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=30)
                logger.info(f"Response status: {response.status_code}, length: {len(response.text)}")
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
                logger.error(f"Error fetching {attempt}: {e}")
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
        data = {
            "package_number": pkg_number,
            "orders": pkg_items,
            "last_update_date": last_update_date,
            "delivered": delivered,
            "is_today": is_today
        }
        if any("ghazala" in u["Lieu"].lower() for u in updates):
            location = "Ghazala"
            in_tunisia += 1
            packages_in_tunisia[location].append(data)
            if not delivered:
                packages_in_tunisia_not_delivered[location].append(data)
        elif any("ariana" in u["Lieu"].lower() for u in updates):
            location = "Ariana"
            in_tunisia += 1
            packages_in_tunisia[location].append(data)
            if not delivered:
                packages_in_tunisia_not_delivered[location].append(data)
        elif any("tunis" in u["Lieu"].lower() for u in updates):
            location = "Tunis"
            in_tunisia += 1
            packages_in_tunisia[location].append(data)
            if not delivered:
                packages_in_tunisia_not_delivered[location].append(data)
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
    separator = "-" * 100
    order_cut = 30
    log_output.append(f"Summary: \n - {found_updates}/{total_packages} packages updates found")
    log_output.append(f" - {in_tunisia}/{found_updates} packages are in Tunisia\n")
    log_output.append(f"Packages in Tunisia by location {('(including delivered)' if show_delivered else '(not delivered only)')}:")
    
    packages_to_show = packages_in_tunisia if show_delivered else packages_in_tunisia_not_delivered
    for loc, pkgs in packages_to_show.items():
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
                    orders += f"\n\t\t\t\t\t\t{o[:order_cut]}..."
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
                orders += f"\n\t\t\t\t\t\t{o[:order_cut]}..."
        log_output.append(orders)
        log_output.append(separator) 
        
    log_output.append(f"\n - No updates: {len(no_update)} packages")
    if no_update:
        log_output.append(separator)
    for res in no_update:
        log_output.append(f"\t{(res['orders'][0][:order_cut] + '...').ljust(order_cut+3)}\t|\t{res['package_number']}")
        log_output.append(separator)

    print("\n".join(log_output))
    with open("update_log.txt", "w", encoding="utf-8") as log_file:
        log_file.write("\n".join(log_output))

    return with_update, no_update, log_output


def create_mobile_output(packages, show_only_updates=True):
    """Create mobile-friendly output format for Telegram bot"""
    base_url = "http://www.rapidposte.poste.tn/fr/Item_Events.asp?ItemId="
    results = []
    total_packages = len(packages)
    found_updates = 0
    in_tunisia = 0
    on_the_way = 0
    show_delivered = False
    packages_in_tunisia = {"Ghazala": [], "Ariana": [], "Tunis": []}
    packages_in_tunisia_not_delivered = {"Ghazala": [], "Ariana": [], "Tunis": []}
    packages_on_the_way = []

    for idx, pkg in enumerate(packages, start=1):
        pkg_number_original = pkg["package_number"]
        pkg_items = pkg.get("package orders", [])

        pkg_numbers_to_try = [pkg_number_original]
        if "/" in pkg_number_original:
            pkg_numbers_to_try = pkg_number_original.split('/')

        soup = None
        pkg_number = None

        for attempt in pkg_numbers_to_try:
            url = base_url + attempt
            try:
                logger.info(f"Fetching URL: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=5)
                logger.info(f"Response status: {response.status_code}, length: {len(response.text)}")
                response.raise_for_status()
                
                temp_soup = BeautifulSoup(response.text, "html.parser")
                if temp_soup.find("table", {"id": "200"}):
                    soup = temp_soup
                    pkg_number = attempt
                    break
            except requests.RequestException:
                continue
        
        if not soup:
            results.append({
                "n°": idx,
                "package_number": pkg_number_original,
                "orders": pkg_items,
                "updates": "no package update"
            })
            continue

        table = soup.find("table", {"id": "200"})
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
        data = {
            "package_number": pkg_number,
            "orders": pkg_items,
            "last_update_date": last_update_date,
            "delivered": delivered,
            "is_today": is_today
        }
        if any("ghazala" in u["Lieu"].lower() for u in updates):
            location = "Ghazala"
            in_tunisia += 1
            packages_in_tunisia[location].append(data)
            if not delivered:
                packages_in_tunisia_not_delivered[location].append(data)
        elif any("ariana" in u["Lieu"].lower() for u in updates):
            location = "Ariana"
            in_tunisia += 1
            packages_in_tunisia[location].append(data)
            if not delivered:
                packages_in_tunisia_not_delivered[location].append(data)
        elif any("tunis" in u["Lieu"].lower() for u in updates):
            location = "Tunis"
            in_tunisia += 1
            packages_in_tunisia[location].append(data)
            if not delivered:
                packages_in_tunisia_not_delivered[location].append(data)
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

    if show_only_updates:
        with_update = [res for res in results if res["updates"] != "no package update"]
        no_update = [res for res in results if res["updates"] == "no package update"]
    else:
        with_update = results
        no_update = []

    # Use the new mobile formatter
    from mobile_formatter import format_mobile_output
    # Pass all results with updates to count delivered packages correctly
    all_results_with_updates = [res for res in results if res["updates"] != "no package update"]
    mobile_output = format_mobile_output(
        results=all_results_with_updates,
        packages_in_tunisia_not_delivered=packages_in_tunisia_not_delivered,
        packages_on_the_way=packages_on_the_way,
        total_packages=total_packages,
        found_updates=found_updates,
        no_update=no_update
    )

    return with_update, no_update, mobile_output


def fetch_single_package(tracking_number, package_orders=None):
    """Fetch detailed information for a single package including full tracking table"""
    if package_orders is None:
        package_orders = []
    
    base_url = "http://www.rapidposte.poste.tn/fr/Item_Events.asp?ItemId="
    
    pkg_numbers_to_try = [tracking_number]
    if "/" in tracking_number:
        pkg_numbers_to_try = tracking_number.split('/')
    
    soup = None
    pkg_number = None
    
    for attempt in pkg_numbers_to_try:
        url = base_url + attempt
        try:
            logger.info(f"Fetching URL: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            logger.info(f"Response status: {response.status_code}, length: {len(response.text)}")
            response.raise_for_status()
            
            temp_soup = BeautifulSoup(response.text, "html.parser")
            if temp_soup.find("table", {"id": "200"}):
                soup = temp_soup
                pkg_number = attempt
                break
        except requests.RequestException as e:
            logger.error(f"Error fetching {attempt}: {e}")
            continue
    
    if not soup:
        return None
    
    table = soup.find("table", {"id": "200"})
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
    
    # Determine location and status
    location = ""
    last_update_date = updates[-1]["Date"] if updates else None
    is_today = False
    if last_update_date:
        try:
            is_today = datetime.now().strftime("%d/%m/%Y") == datetime.strptime(last_update_date, "%d/%m/%Y %H:%M:%S").strftime("%d/%m/%Y")
        except:
            pass
    
    delivered = any("Livré" in u["Type d'événement"] for u in updates)
    
    if any("ghazala" in u["Lieu"].lower() for u in updates):
        location = "Ghazala"
    elif any("ariana" in u["Lieu"].lower() for u in updates):
        location = "Ariana"
    elif any("tunis" in u["Lieu"].lower() for u in updates):
        location = "Tunis"
    else:
        location = "on the way"
    
    return {
        "package_number": pkg_number,
        "orders": package_orders,
        "updates": updates,
        "location": location,
        "delivered": delivered,
        "is_today": is_today,
        "last_update_date": last_update_date
    }


def load_packages_from_file(path="package_list.json"):
    """Load package list from a JSON file and return it.

    This helper makes the module import-safe so other scripts (like a bot)
    can import fetch_package_updates without running the script on import.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    packages_list = load_packages_from_file()
    fetch_package_updates(packages_list, show_only_updates=True)
