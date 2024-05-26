from selenium import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from os.path import join, dirname
import os

# copied from minetracker-lambda:
def process_scraped_minesweeper_game(result_block_text, difficulty_selector_html, username):
    """
    given the text from a minesweeper game result block and the html of the difficulty selector,
    parse out all relevant statistics and the actual difficulty of the game.
    verifies that the username provided is the user that played the game; raise an exception if not.
    """
    # validate the game was played by the desired user
    if username not in result_block_text:
        raise
    
    # parse the difficulty from the HTML
    difficulty = ""
    if "Expert" in difficulty_selector_html:
        difficulty = "expert"
    elif "Intermediate" in difficulty_selector_html:
        difficulty = "intermediate"
    elif "Beginner" in difficulty_selector_html:
        difficulty = "beginner"
    else:
        difficulty = "other"

    # parse (and calculate) other relevant stats
    split_result_text = result_block_text.split('\n')

    # calculate time elapsed playing the game
    game_time_line = next((x for x in split_result_text if x.startswith("Time:")), "")
    elapsed_time_value = -1.0 if not game_time_line else float(game_time_line.split(' ')[1])

    # calculate the time minesweeper estimated the game would have taken
    game_estimated_time_line = next((x for x in split_result_text if x.startswith("Estimated time:")), "")
    estimated_time_value = -1.0 if not game_estimated_time_line else float(game_estimated_time_line.split(": ")[1])

    # calculate the 3bv values
    game_3bv_line = next((x for x in split_result_text if x.startswith("3BV:")), "")
    raw_3bv_value = "" if not game_3bv_line else game_3bv_line.split(": ")[1]
    board_solved = ('/' not in raw_3bv_value)
    completed_3bv_value = int(raw_3bv_value) if board_solved else int(raw_3bv_value.split(" / ")[0])
    board_3bv_value = int(raw_3bv_value) if board_solved else int(raw_3bv_value.split(" / ")[1])

    # calculate the 3bvp/s value
    game_3bvps_line = next((x for x in split_result_text if x.startswith("3BV/s:")), "")
    the_3bvps_value = -1.0 if not game_3bvps_line else float(game_3bvps_line.split(' ')[1])

    # calculate click values
    game_clicks_line = next((x for x in split_result_text if x.startswith("Clicks:")), "")
    raw_clicks_value = "" if not game_clicks_line else game_clicks_line.split(": ")[1]
    useful_clicks_value = -1.0 if not raw_clicks_value else int(raw_clicks_value.split('+')[0])
    wasted_clicks_value = -1.0 if not raw_clicks_value else int(raw_clicks_value.split('+')[1])
    total_clicks_value = useful_clicks_value + wasted_clicks_value

    # calculate efficiency value
    game_efficiency_line = next((x for x in split_result_text if x.startswith("Efficiency:")), "")
    efficiency_string = "" if not game_efficiency_line else game_efficiency_line.split(' ')[1]
    efficiency_value = -1.0 if not efficiency_string else float(efficiency_string.strip().strip('%'))

    # calculate solved percentage
    solve_percentage_value = 100.0 if board_solved else (float(completed_3bv_value)/float(board_3bv_value)) * 100.0

    # create return objects and return
    statistics = {
        "elapsed-time": elapsed_time_value,
        "estimated-time": estimated_time_value,
        "board-solved": board_solved,
        "completed-3bv": completed_3bv_value,
        "board-3bv": board_3bv_value,
        "game-3bvps": the_3bvps_value,
        "useful-clicks": useful_clicks_value,
        "wasted-clicks": wasted_clicks_value,
        "total-clicks": total_clicks_value,
        "efficiency": efficiency_value,
        "solve-percentage": solve_percentage_value
    }
    return (statistics, difficulty)

# load dotenv
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# these are pulled from minetracker-lambda's main.py:
# from scrape_minesweeper_online_game:
options = webdriver.ChromeOptions()
service = webdriver.ChromeService("/usr/local/bin/chromedriver")
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-dev-tools")
options.add_argument("--no-zygote")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")

# according to https://stackoverflow.com/questions/27630190/python-selenium-incognito-private-mode,
# selenium uses a private profile by default, so don't have to worry about this access being logged to history at all.
driver = webdriver.Chrome(options=options, service=service)
driver.get(os.environ['MINESWEEPER_CHECK_URL'])
driver.implicitly_wait(8)

try:
    result_block = driver.find_element(By.CLASS_NAME, "result-block")
    # alternate way to find, if necessary:
    # result_block = driver.find_element(By.XPATH, "//*[@id='result_absolute_right_block']/div")
    result_block_text = result_block.text

    difficulty_selector = driver.find_element(By.XPATH, "//button[@class='btn btn-sm btn-default btn-level-select dropdown-toggle']")
    # alternate way to find, if necessary:
    # difficulty_selector = driver.find_element(By.CLASS_NAME, "btn btn-sm btn-default btn-level-select dropdown-toggle")
    difficulty_selector_html = difficulty_selector.get_attribute("innerHTML")

    driver.quit()
    result = process_scraped_minesweeper_game(result_block_text, difficulty_selector_html, os.environ['MINESWEEPER_USERNAME'])
    assert result[1] == "expert"
    assert result[0]["elapsed-time"] == 65.189
    assert result[0]["board-3bv"] == 128
    assert result[0]["game-3bvps"] == 1.9635
    assert result[0]["efficiency"] == 66
    assert result[0]["useful-clicks"] == 179
    assert result[0]["wasted-clicks"] == 14
    print("SUCCESS: validation of scraping finished with expected values.")
except AssertionError as ae:
    print("FAILURE: processing of scraped game failed during validation; key statistics were not as expected. is a manual check necessary?")
    raise ae
except Exception as e:
    driver.quit()
    print("FAILURE: unable to scrape game content during validation. is minesweeper.online down?")
    raise e
