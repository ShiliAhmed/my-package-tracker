def format_single_package_detail(package_result):
    """Format detailed output for a single package check with full tracking table"""
    
    output = []
    
    # Package header
    output.append("📦 PACKAGE DETAILS")
    output.append("━━━━━━━━━━━━━━━")
    output.append("")
    
    # Package number
    pkg_number = package_result.get("package_number", "N/A")
    output.append(f"📋 Tracking: {pkg_number}")
    output.append("")
    
    # All orders
    orders = package_result.get("orders", [])
    if orders:
        output.append("🛍️ Orders in this package:")
        for i, order in enumerate(orders, 1):
            if len(order) > 50:
                order = order[:47] + "..."
            output.append(f"  {i}. {order}")
        output.append("")
    
    # Status info
    if package_result.get("delivered"):
        output.append("✅ Status: Delivered")
    else:
        location = package_result.get("location", "Unknown")
        if location != "on the way":
            output.append(f"📍 Location: {location}")
        else:
            output.append("🚚 Status: On the way")
    
    if package_result.get("is_today"):
        output.append("✨ Updated today")
    
    output.append("")
    
    # Full tracking table
    updates = package_result.get("updates", [])
    if updates:
        output.append("📋 TRACKING HISTORY")
        output.append("━━━━━━━━━━━━━━━")
        output.append("")
        
        # Show updates in reverse order (newest first)
        for i, update in enumerate(reversed(updates), 1):
            date = update.get("Date", "N/A")
            pays = update.get("Pays", "N/A")
            lieu = update.get("Lieu", "N/A")
            event = update.get("Type d'événement", "N/A")
            
            output.append(f"┌─ Event #{len(updates) - i + 1}")
            output.append(f" │  📅 {date}")
            output.append(f" │  🌍 {pays}")
            output.append(f" │  📍 {lieu}")
            output.append(f" │  📝 {event}")
            output.append("└─" if i == len(updates) else "├─")
            output.append("")
    else:
        output.append("❌ No tracking history found")
        output.append("")
    
    return output

