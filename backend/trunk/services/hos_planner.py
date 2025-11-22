from datetime import datetime, timedelta
from decimal import Decimal

def plan_hos_compliant_trip(total_driving_seconds: int, cycle_used_hours: Decimal):
    total_driving_hours = round(total_driving_seconds / 3600, 2)
    driving_left = Decimal(str(total_driving_hours))
    cycle_used = Decimal(cycle_used_hours)
    remaining_cycle = Decimal('70') - cycle_used

    daily_plan = []
    day = 1
    current_time = datetime.now().replace(hour=5, minute=0, second=0, microsecond=0)
    cumulative_driving = Decimal('0')

    while driving_left > Decimal('0.1'):
        day_entry = {
            "day": day,
            "date": current_time.strftime("%Y-%m-%d"),
            "start_time": current_time.strftime("%H:%M"),
            "driving_hours": 0.0,
            "on_duty_hours": 0.0,
            "events": [],
            "fuel_stop": False,
            "includes_30min_break": False,
            "off_duty_start": "",
            "next_day_start": ""
        }

        # How much driving can we do today?
        max_driving_today = min(Decimal('11.0'), remaining_cycle)
        driving_today = min(max_driving_today, driving_left)

        # 30-minute break if driving > 8 hours
        break_needed = driving_today > Decimal('8.0')
        on_duty_today = driving_today
        if break_needed:
            on_duty_today += Decimal('0.5')
            day_entry["includes_30min_break"] = True

        # Pickup on day 1, dropoff on last day
        if day == 1:
            on_duty_today += Decimal('1.0')  # pickup
        if driving_left <= driving_today + Decimal('0.5'):  # last day
            on_duty_today += Decimal('1.0')  # dropoff

        # Fuel stop every ~1000 miles
        cumulative_driving += driving_today
        if cumulative_driving >= Decimal('950') and not any(d.get("fuel_stop") for d in daily_plan):
            day_entry["fuel_stop"] = True
            day_entry["events"].append("30-min fuel stop")

        # Final numbers (convert to float only for display)
        day_entry["driving_hours"] = round(float(driving_today), 1)
        day_entry["on_duty_hours"] = round(float(on_duty_today), 1)
        day_entry["events"].append(f"Drive {round(float(driving_today), 1)}h")

        # 14-hour window + 10-hour reset
        off_duty_start = current_time + timedelta(hours=14)
        off_duty_end = off_duty_start + timedelta(hours=10)

        day_entry["off_duty_start"] = off_duty_start.strftime("%H:%M")
        day_entry["next_day_start"] = off_duty_end.strftime("%H:%M (+1 day)")

        daily_plan.append(day_entry)

        # Update counters
        driving_left -= driving_today
        cycle_used += on_duty_today
        remaining_cycle = Decimal('70') - cycle_used

        # 34-hour restart if needed
        if remaining_cycle <= 0 and driving_left > Decimal('0.1'):
            daily_plan.append({
                "day": "RESET",
                "event": "34-HOUR RESTART",
                "note": "Required to regain 70-hour cycle"
            })
            current_time += timedelta(hours=34)
            cycle_used = Decimal(cycle_used_hours)  # reset cycle
            remaining_cycle = Decimal('70') - cycle_used
        else:
            current_time = off_duty_end

        day += 1

    # Final summary
    total_on_duty_added = sum(Decimal(str(d["on_duty_hours"])) for d in daily_plan if "on_duty_hours" in d)
    final_remaining = Decimal('70') - (Decimal(cycle_used_hours) + total_on_duty_added)

    return {
        "total_days_needed": len([d for d in daily_plan if isinstance(d.get("day"), int)]),
        "total_on_duty_hours": round(float(total_on_duty_added), 1),
        "remaining_cycle_after_trip": max(0, round(float(final_remaining), 1)),
        "requires_34h_reset": any("34-HOUR" in str(d) for d in daily_plan),
        "daily_plan": daily_plan
    }