from datetime import datetime


def format_mobile_output(results, packages_in_tunisia_not_delivered, packages_on_the_way, 
                         total_packages, found_updates, no_update):
    """Create mobile-friendly output with updated summary format"""
    
    mobile_output = []
    
    # Header
    mobile_output.append("📦 PACKAGE TRACKER")
    mobile_output.append("━━━━━━━━━━━━━━━")
    mobile_output.append("")
    
    # Calculate summary statistics
    delivered_count = sum(1 for res in results if res.get("delivered", False))
    non_delivered_count = found_updates - delivered_count
    in_tunisia_not_delivered = sum(len(pkgs) for pkgs in packages_in_tunisia_not_delivered.values())
    on_the_way_count = len(packages_on_the_way)
    
    # Summary Section
    mobile_output.append("📊 SUMMARY")
    mobile_output.append(f"• Updates found: {found_updates}/{total_packages}")
    mobile_output.append(f"• Delivered: {delivered_count}")
    mobile_output.append(f"• Non-delivered (ND): {non_delivered_count}")
    mobile_output.append(f"• In Tunisia (ND): {in_tunisia_not_delivered}")
    mobile_output.append(f"• On the way: {on_the_way_count}")
    mobile_output.append("")
    
    # Packages in Tunisia (not delivered)
    if in_tunisia_not_delivered > 0:
        mobile_output.append("📍 TUNISIA")
        mobile_output.append("━━━━━━━━━━━━━━━")
        mobile_output.append("")
        
        for loc, pkgs in packages_in_tunisia_not_delivered.items():
            if pkgs:
                mobile_output.append(f"🏢 {loc} ({len(pkgs)})")
                for i, p in enumerate(pkgs):
                    # Package number
                    mobile_output.append(f"┌─ {p['package_number']}")
                    
                    # First order description (truncated for mobile)
                    first_order = p['orders'][0]
                    if len(first_order) > 30:
                        first_order = first_order[:27] + "..."
                    mobile_output.append(f" │  📝 {first_order}")
                    
                    # Additional orders if any
                    if len(p['orders']) > 1:
                        for o in p['orders'][1:]:
                            if len(o) > 30:
                                o = o[:27] + "..."
                            mobile_output.append(f" │  📝 {o}")
                    
                    # Last update date
                    mobile_output.append(f" │  🕐 {p['last_update_date']}")
                    
                    # Status indicators
                    status_indicators = []
                    if p['is_today']:
                        status_indicators.append("✨ Today")
                    
                    if status_indicators:
                        mobile_output.append(f" │  {' '.join(status_indicators)}")
                    
                    # Close the package block
                    mobile_output.append("└─" if i == len(pkgs) - 1 else "├─")
                mobile_output.append("")
    
    # Packages on the way
    if packages_on_the_way:
        mobile_output.append(f"🚚 ON THE WAY ({on_the_way_count})")
        mobile_output.append("━━━━━━━━━━━━━━━")
        mobile_output.append("")
        
        for i, p in enumerate(packages_on_the_way):
            # Package number
            mobile_output.append(f"┌─ {p['package_number']}")
            
            # First order description (truncated for mobile)
            first_order = p['orders'][0]
            if len(first_order) > 30:
                first_order = first_order[:27] + "..."
            mobile_output.append(f" │  📝 {first_order}")
            
            # Additional orders if any
            if len(p['orders']) > 1:
                for o in p['orders'][1:]:
                    if len(o) > 30:
                        o = o[:27] + "..."
                    mobile_output.append(f" │  📝 {o}")
            
            # Last update date
            mobile_output.append(f" │  🕐 {p['last_update_date']}")
            
            # Status indicators
            if p['is_today']:
                mobile_output.append(" │  ✨ Today")
            
            # Close the package block
            mobile_output.append("└─" if i == len(packages_on_the_way) - 1 else "├─")
        mobile_output.append("")
    
    # No updates
    if no_update:
        mobile_output.append("❌ NO UPDATES")
        mobile_output.append("━━━━━━━━━━━━━━━")
        mobile_output.append("")
        
        for i, res in enumerate(no_update):
            first_order = res['orders'][0]
            if len(first_order) > 30:
                first_order = first_order[:27] + "..."
            mobile_output.append(f"┌─ {res['package_number']}")
            mobile_output.append(f" │  📝 {first_order}")
            mobile_output.append(" │  ❌ No updates found")
            mobile_output.append("└─" if i == len(no_update) - 1 else "├─")
        mobile_output.append("")

    return mobile_output

