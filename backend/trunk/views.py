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

            # Calculate graph positions (FMCSA official scale: 1 hour = 40px)
            start_hour = 5  # 5 AM
            pickup_end = start_hour + 1
            driving_start = pickup_end
            driving_end = driving_start + day['driving_hours']
            break_inserted = day.get('includes_30min_break', False)
            break_at = driving_start + 8 if break_inserted else driving_end
            off_duty_at = 19  # ~14-hour window from 5 AM

            logs_html += f"""
            <div class="log-page">
                <div class="header">
                    <h2>DRIVER'S RECORD OF DUTY STATUS (GRAPH GRID)</h2>
                    <p class="subtitle">FMCSA Property-Carrying • 70-Hour/8-Day Rule • §395.8</p>
                </div>

                <table class="info-table">
                    <tr><td><strong>Date:</strong> {day['date']}</td><td><strong>24-Hour Period Starting Time:</strong> {day['start_time']}</td></tr>
                    <tr><td><strong>Driver Name:</strong> _________________________</td><td><strong>Truck/Tractor #: ________ Trailer #: ________</td></tr>
                    <tr><td><strong>Main Office Address:</strong> {trip.current_location}</td><td><strong>Home Terminal:</strong> {trip.current_location}</td></tr>
                    <tr><td colspan="2"><strong>Shipping Document # or Trip:</strong> {trip.pickup_location} → {trip.dropoff_location}</td></tr>
                </table>

                <div class="graph-grid">
                    <div class="hours-labels">
                        {"".join(f'<div class="hour" style="left:{40*(i)}px">{i}</div>' for i in range(25))}
                    </div>
                    <svg width="960" height="200" viewBox="0 0 960 200">
                        <!-- Grid lines -->
                        <g stroke="#ccc">
                            {"".join(f'<line x1="{40*i}" y1="0" x2="{40*i}" y2="200"/>' for i in range(25))}
                        </g>
                        <!-- Duty Status Lines (FMCSA exact order) -->
                        <!-- Line 1: Off Duty -->
                        <line x1="{40*0}" y1="20" x2="{40*pickup_end}" y2="20" stroke="black" stroke-width="6"/>
                        <line x1="{40*off_duty_at}" y1="20" x2="960" y2="20" stroke="black" stroke-width="6"/>
                        
                        <!-- Line 2: Sleeper Berth (not used) -->
                        
                        <!-- Line 3: Driving -->
                        <line x1="{40*driving_start}" y1="80" x2="{40*driving_end}" y2="80" stroke="#0066cc" stroke-width="8"/>
                        
                        <!-- Line 4: On Duty Not Driving -->
                        <line x1="{40*pickup_end}" y1="140" x2="{40*driving_start}" y2="140" stroke="#ff9900" stroke-width="8"/>
                        <!-- 30-min break if needed -->
                        {f'<line x1="{40*break_at}" y1="140" x2="{40*(break_at+0.5)}" y2="140" stroke="#ff9900" stroke-width="8"/>' if break_inserted else ''}
                    </svg>

                    <div class="legend">
                        <span><strong>Line 1:</strong> Off Duty</span> |
                        <span><strong>Line 3:</strong> Driving</span> |
                        <span><strong>Line 4:</strong> On Duty (Not Driving)</span>
                    </div>
                </div>

                <table class="totals">
                    <tr><td>Total Miles Driven Today:</td><td>~{int(trip.total_distance_miles / trip.hos_plan['total_days_needed'])} mi</td></tr>
                    <tr><td>Driving Today:</td><td>{day['driving_hours']} hours</td></tr>
                    <tr><td>On Duty Today:</td><td>{day['on_duty_hours']} hours</td></tr>
                    <tr><td>Remarks:</td><td>{'30-min break taken' if day.get('includes_30min_break') else ''} {'| Fuel stop' if day.get('fuel_stop') else ''}</td></tr>
                </table>

                <div class="signature">
                    <p>I certify that this log is true and correct.</p>
                    <p>Driver Signature: _________________________________________ Date: __________</p>
                </div>
                <div class="page-break"></div>
            </div>
            """
        
        full_css = """
        <style>
            @page { size: Letter; margin: 0.5in; }
            body { font-family: Arial, sans-serif; margin: 0; background: #f9f9f9; }
            .log-page { background: white; padding: 30px; margin: 20px auto; width: 8.5in; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
            .header { text-align: center; border-bottom: 4px solid #003366; padding-bottom: 10px; margin-bottom: 20px; }
            .header h2 { margin: 0; color: #003366; font-size: 20px; }
            .subtitle { margin: 5px 0; color: #003366; font-weight: bold; }
            .info-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            .info-table td { padding: 8px; border: 1px solid #000; background: #f0f0f0; }
            .graph-grid { margin: 30px 0; border: 3px solid black; background: white; position: relative; }
            .hours-labels { position: absolute; top: -20px; left: 40px; }
            .hour { position: absolute; font-size: 10px; width: 40px; text-align: center; }
            .legend { text-align: center; margin: 10px 0; font-size: 14px; }
            .totals { width: 100%; border-collapse: collapse; margin: 20px 0; }
            .totals td { padding: 10px; border: 1px solid black; }
            .signature { margin-top: 50px; text-align: center; font-size: 14px; }
            .page-break { page-break-after: always; }
            @media print { body { background: white; } .page-break { page-break-after: always; } }
            button { position: fixed; top: 20px; right: 20px; padding: 15px 30px; background: #003366; color: white; font-size: 18px; border: none; cursor: pointer; z-index: 1000; }
        </style>
        """

        return HttpResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>FMCSA Logs - {str(trip.id)[:8]}</title>
            {full_css}
        </head>
        <body>
            <button onclick="window.print()">PRINT ALL LOGS</button>
            <h1 style="text-align:center; color:#003366; margin:30px;">OFFICIAL FMCSA DAILY LOGS</h1>
            {logs_html}
        </body>
        </html>
        """, content_type="text/html")