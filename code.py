import time
import board
from adafruit_matrixportal.matrixportal import MatrixPortal

# --- Data Setup --- #
DISPLAY_NUM_GUIDES = 4  # Show next four trains
DATA_SOURCE = "https://api-v3.mbta.com/predictions?filter%5Bstop%5D=place-wondl&filter%5Bdirection_id%5D=0&filter%5Broute%5D=Blue&page%5Blimit%5D=6&sort=departure_time"

matrixportal = MatrixPortal(
    url=DATA_SOURCE,
    status_neopixel=board.NEOPIXEL,
)

# --- Display Setup --- #
FONT = "/fonts/tom-thumb.bdf"  # Smaller font
TEXT_COLORS = (0xff1d1d, 0x5c85ff, 0xa300a3, 0xadebad)  # , Blue, Purple, Green
SCROLL_DELAY = 0.03  # Adjust scrolling speed (lower is faster)

# Add Text Labels for Train Times (One for each train)
text_ids = []
for i in range(DISPLAY_NUM_GUIDES):
    text_id = matrixportal.add_text(
        text_font=FONT,
        text_position=(0, ((i * 8) + 3)),  # Adjust vertical spacing for smaller font
        text_color=TEXT_COLORS[i % len(TEXT_COLORS)],  # Cycle through colors
        scrolling=True,  # Enable scrolling for this label
    )
    text_ids.append(text_id)

def format_time(dt_str):
    """Formats datetime string into HH:MM AM/PM"""
    time_part = dt_str.split("T")[1].split("-")[0]  # Extract "19:15:00"
    hour, minute, _ = map(int, time_part.split(":"))  # Split into hours and minutes
    am_pm = "AM" if hour < 12 else "PM"
    hour = hour if hour <= 12 else hour - 12
    return f"{hour}:{minute:02} {am_pm}"

def get_train_times():
    """Fetch train departure times and return formatted list."""
    print("Fetching MBTA data...")
    try:
        als_data = matrixportal.network.fetch(DATA_SOURCE)
        train_data = matrixportal.network.json_traverse(als_data.json(), ["data"])

        if len(train_data) < DISPLAY_NUM_GUIDES:
            print("Warning: Less than four train times available")
            return ["No Data"] * DISPLAY_NUM_GUIDES

        train_times = []
        for i in range(DISPLAY_NUM_GUIDES):
            departure_time = train_data[i]["attributes"]["departure_time"]
            formatted_time = format_time(departure_time)
            train_times.append(formatted_time)

        print(f"Next four trains: {train_times}")
        return train_times

    except Exception as e:
        print("Error fetching train times:", e)
        return ["Error"] * DISPLAY_NUM_GUIDES

def update_display(train_times):
    """Update the display with scrolling text for each train."""
    for i, train_time in enumerate(train_times):
        label_text = f"Train {i+1}: {train_time}"
        matrixportal.set_text(label_text, text_ids[i])

refresh_time = None
while True:
    if (not refresh_time) or (time.monotonic() - refresh_time) > 900:
        try:
            print("Updating system time...")
            matrixportal.get_local_time()
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Time sync failed, retrying -", e)
            continue

    train_times = get_train_times()
    update_display(train_times)  # Update display with new train times

    # Scroll all labels simultaneously using built-in functionality
    matrixportal.scroll_text(SCROLL_DELAY)
