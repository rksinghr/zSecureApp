from django.shortcuts import render

def dashboard(request):
    context = {
        "stats": {
            "revenue": 128450,
            "orders": 1842,
            "customers": 624,
            "conversion_rate": 4.8,
        },
        "recent_orders": [
            {"id": "#10482", "customer": "Aarav Sharma", "amount": 2499, "status": "Completed"},
            {"id": "#10481", "customer": "Priya Reddy", "amount": 5890, "status": "Processing"},
            {"id": "#10480", "customer": "Rahul Kumar", "amount": 1299, "status": "Completed"},
        ],
        "chart_data": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "values": [12000, 18500, 14200, 22400, 19800, 28600, 32100],
        },
    }

    return render(request, "appMain/dashboard.html", context)
