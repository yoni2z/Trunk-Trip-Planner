from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Trip
from .serializers import TripSerializer
from .services.routing import geocode_location, get_truck_route
from .services.hos_planner import plan_hos_compliant_trip
from datetime import datetime
from decimal import Decimal
import json

import os
from rest_framework.decorators import action
from rest_framework.response import Response
from .services.logsheet_generator import generate_daily_log_pdf
import zipfile
import io
from django.http import HttpResponse
from datetime import datetime

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().order_by('-created_at')
    serializer_class = TripSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Geocode locations
        locations = [
            request.data['current_location'],
            request.data['pickup_location'],
            request.data['dropoff_location']
        ]
        coords = []
        for loc in locations:
            coord = geocode_location(loc)
            if not coord:
                return Response({"message": f"Could not find location: {loc}"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            coords.append(coord)

        # Get route
        route_data = get_truck_route(coords)
        if not route_data or 'routes' not in route_data:
            return Response({"message": "Route calculation failed"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        route = route_data['routes'][0]
        summary = route['summary']
        total_miles = Decimal(summary['distance'])
        total_hours = Decimal(summary['duration']) / 3600

        # CRITICAL FIX: Convert Decimal → float before JSON
        total_miles_float = float(total_miles)
        total_hours_float = round(float(total_hours), 2)

        # Build clean summary with only JSON-serializable types
        route_summary_clean = {
            "total_distance_miles": total_miles_float,
            "total_driving_hours": total_hours_float,
            "segments": [
                {
                    "from": locations[0],
                    "to": locations[1],
                    "miles": total_miles_float * 0.4,  # placeholder split
                    "hours": total_hours_float * 0.4
                },
                {
                    "from": locations[1],
                    "to": locations[2],
                    "miles": total_miles_float * 0.6,
                    "hours": total_hours_float * 0.6
                }
            ]
        }

        # Save trip — now safe for JSONField
        trip = serializer.save(
            total_distance_miles=total_miles,
            total_driving_hours=total_hours,
            route_raw=route_data,
            route_summary=route_summary_clean,   # ← Now 100% JSON-safe
            status="route_calculated"
        )

        total_driving_seconds = route['summary']['duration']  # this is in seconds

        # Run HOS planner
        hos_result = plan_hos_compliant_trip(
            total_driving_seconds=int(total_driving_seconds),
            cycle_used_hours=Decimal(str(request.data['cycle_used_hours']))
        )

        # Save HOS plan
        trip.hos_plan = hos_result
        trip.hos_computed_at = datetime.now()
        trip.status = "hos_compliant"
        trip.save()

        return Response({
            "trip_id": str(trip.id)[:8].upper(),
            "message": "Route calculated successfully!",
            "route": route_summary_clean,
            "hos": hos_result
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='logs')
    def print_logs(self, request, pk=None):
        trip = self.get_object()
        if not trip.hos_plan:
            return Response({"error": "No HOS plan"}, status=400)

        logs_html = ""
        for day in trip.hos_plan["daily_plan"]:
            if not isinstance(day.get("day"), int):
                continue

            start_hour = 5
            pickup_end = start_hour + 1
            driving_start = pickup_end
            driving_end = driving_start + day['driving_hours']
            break_inserted = day.get('includes_30min_break', False)
            break_at = driving_start + 8 if break_inserted else driving_end
            off_duty_at = start_hour + 14

            logs_html += f"""
            <div class="log-page">
                <div class="fmsca-header">
                    <h1>DRIVER'S RECORD OF DUTY STATUS</h1>
                    <p class="rule">Property-Carrying • 70-Hour/8-Day Rule • §395.8</p>
                </div>

                <table class="info-grid">
                    <tr><td class="label">Date:</td><td>{day['date']}</td><td class="label">24-Hour Period Starting:</td><td>{day['start_time']}</td></tr>
                    <tr><td class="label">Driver Name:</td><td colspan="3" class="underline">________________________________________________</td></tr>
                    <tr><td class="label">Main Office:</td><td>{trip.current_location}</td><td class="label">Home Terminal:</td><td>{trip.current_location}</td></tr>
                    <tr><td class="label">Trip:</td><td colspan="3">{trip.pickup_location} to {trip.dropoff_location}</td></tr>
                </table>

                <div class="graph-container">
                    <div class="hour-labels">
                        {"".join(f'<span style="left: calc({i} * 4.1666%)">{i}</span>' for i in range(25))}
                    </div>
                    <svg viewBox="0 0 1200 400" preserveAspectRatio="xMidYMid meet">
                        <!-- 4 Official Horizontal Lines -->
                        <line x1="0" y1="80"  x2="1200" y2="80"  stroke="#ccc" stroke-width="3"/>  <!-- Line 1: Off Duty -->
                        <line x1="0" y1="160" x2="1200" y2="160" stroke="#ccc" stroke-width="3"/>  <!-- Line 2: Sleeper Berth -->
                        <line x1="0" y1="240" x2="1200" y2="240" stroke="#ccc" stroke-width="3"/>  <!-- Line 3: Driving -->
                        <line x1="0" y1="320" x2="1200" y2="320" stroke="#ccc" stroke-width="3"/>  <!-- Line 4: On Duty ND -->

                        <!-- Vertical grid -->
                        <g stroke="#ddd" stroke-width="1">
                            {"".join(f'<line x1="{50*i}" y1="40" x2="{50*i}" y2="360"/>' for i in range(25))}
                        </g>

                        <!-- ACTUAL DUTY STATUS LINES (THICK & COLORED) -->
                        <!-- Line 1: Off Duty (Black) -->
                        <line x1="0" y1="80" x2="{50*pickup_end}" y2="80" stroke="black" stroke-width="12"/>
                        <line x1="{50*off_duty_at}" y1="80" x2="1200" y2="80" stroke="black" stroke-width="12"/>

                        <!-- Line 2: Sleeper Berth (Gray) — NOT USED IN THIS PLAN -->
                        <!-- (Left empty — correct for property-carrying) -->

                        <!-- Line 3: Driving (Blue) -->
                        <line x1="{50*driving_start}" y1="240" x2="{50*driving_end}" y2="240" stroke="#0066cc" stroke-width="14"/>

                        <!-- Line 4: On Duty Not Driving (Orange) -->
                        <line x1="{50*pickup_end}" y1="320" x2="{50*driving_start}" y2="320" stroke="#ff9900" stroke-width="14"/>
                        {f'<line x1="{50*break_at}" y1="320" x2="{50*(break_at + 0.5)}" y2="320" stroke="#ff9900" stroke-width="14"/>' if break_inserted else ''}

                        <!-- Legend -->
                        <text x="20" y="390" font-size="18" fill="#000" font-weight="bold">
                            Line 1: Off Duty | Line 2: Sleeper Berth | Line 3: Driving | Line 4: On Duty (Not Driving)
                        </text>
                    </svg>
                </div>

                <table class="totals">
                    <tr><td>Total Miles Today:</td><td>~{int(trip.total_distance_miles / trip.hos_plan['total_days_needed'])} mi</td></tr>
                    <tr><td>Driving:</td><td>{day['driving_hours']} hours</td></tr>
                    <tr><td>On Duty:</td><td>{day['on_duty_hours']} hours</td></tr>
                    <tr><td>Remarks:</td><td>
                        {'30-minute break taken' if break_inserted else 'None'}
                        {', Fuel stop' if day.get('fuel_stop') else ''}
                    </td></tr>
                </table>

                <div class="signature">
                    <p>I certify this log is true and correct.</p>
                    <p>Driver Signature: _________________________________________ Date: __________</p>
                </div>
            </div>
            """

        css = """
        <style>
            @page { size: landscape letter; margin: 0.5in; }
            body { font-family: Arial, sans-serif; margin: 0; background: #f8f9fa; }
            .log-page { background: white; padding: 40px; margin: 20px auto; max-width: 11in; box-shadow: 0 5px 25px rgba(0,0,0,0.15); page-break-after: always; }
            .fmsca-header { text-align: center; border-bottom: 6px solid #002856; padding: 20px; background: #002856; color: white; margin-bottom: 30px; }
            .fmsca-header h1 { margin: 0; font-size: 32px; }
            .rule { font-size: 18px; margin: 10px 0; }
            .info-grid { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 15px; }
            .info-grid td { padding: 12px; border: 2px solid #333; }
            .info-grid .label { background: #e3f2fd; font-weight: bold; width: 28%; }
            .underline { border-bottom: 2px solid #000; display: inline-block; width: 95%; }
            .graph-container { position: relative; width: 1200px; margin: 40px auto; }
            .hour-labels { position: absolute; top: -35px; width: 1200px; }
            .hour-labels span { position: absolute; font-weight: bold; font-size: 14px; transform: translateX(-50%); }
            svg { border: 5px solid black; background: white; width: 1200px; height: 400px; }
            .totals { width: 70%; margin: 30px auto; border-collapse: collapse; font-size: 18px; }
            .totals td { padding: 15px; border: 2px solid black; }
            .totals td:first-child { background: #f0f0f0; font-weight: bold; }
            .signature { margin-top: 60px; text-align: center; font-size: 18px; }
            button { position: fixed; top: 20px; right: 40px; padding: 20px 50px; background: #002856; color: white; font-size: 22px; border: none; border-radius: 10px; cursor: pointer; box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
            @media print { button { display: none; } body { background: white; } }
        </style>
        """

        return HttpResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>FMCSA Official Logs</title>
            {css}
        </head>
        <body>
            <button onclick="window.print()">PRINT ALL LOGS</button>
            <h1 style="text-align:center; color:#002856; margin:50px 0; font-size:40px;">OFFICIAL FMCSA DAILY LOGS</h1>
            {logs_html}
        </body>
        </html>
        """, content_type="text/html")