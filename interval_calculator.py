from datetime import datetime

class IntervalCalculator:
    @staticmethod
    def calculate_by_dates(klines, start_date_str, end_date_str):
        if not klines:
            return None

        # Filter klines by date string range YYYY-MM-DD
        filtered = [
            k for k in klines
            if start_date_str <= k["date"] <= end_date_str
        ]

        if not filtered:
            # Fallback to last bar if out of range
            filtered = [klines[-1]]

        start_bar = filtered[0]
        end_bar = filtered[-1]

        start_price = start_bar["open"]
        end_price = end_bar["close"]

        change_val = round(end_price - start_price, 3)
        pct_change = round((change_val / start_price * 100.0) if start_price > 0 else 0.0, 2)

        max_price = max(k["high"] for k in filtered)
        min_price = min(k["low"] for k in filtered)
        total_volume = sum(k["volume"] for k in filtered)

        return {
            "start_date": start_bar["date"],
            "end_date": end_bar["date"],
            "start_price": start_price,
            "end_price": end_price,
            "change_val": change_val,
            "pct_change": pct_change,
            "max_price": max_price,
            "min_price": min_price,
            "total_volume": total_volume,
            "bar_count": len(filtered)
        }

    @staticmethod
    def calculate_by_preset(klines, preset_key):
        if not klines:
            return None

        total_count = len(klines)
        if total_count == 0:
            return None

        if preset_key == "1w":
            count = 5
        elif preset_key == "1m":
            count = 20
        elif preset_key == "3m":
            count = 60
        elif preset_key == "6m":
            count = 120
        elif preset_key == "1y":
            count = 250
        elif preset_key == "10p":
            count = 10
        elif preset_key == "20p":
            count = 20
        elif preset_key == "60p":
            count = 60
        elif preset_key == "ytd":
            # Year-to-date: from first trading day of current year
            current_year = klines[-1]["date"].split("-")[0]
            ytd_klines = [k for k in klines if k["date"].startswith(current_year)]
            if ytd_klines:
                start_date_str = ytd_klines[0]["date"]
                end_date_str = ytd_klines[-1]["date"]
                return IntervalCalculator.calculate_by_dates(klines, start_date_str, end_date_str)
            else:
                count = 20
        else:
            count = 20

        count = min(count, total_count)
        sub_klines = klines[-count:]

        start_date_str = sub_klines[0]["date"]
        end_date_str = sub_klines[-1]["date"]

        return IntervalCalculator.calculate_by_dates(klines, start_date_str, end_date_str)
