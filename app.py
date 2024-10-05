from flask import Flask, render_template, request, send_file
import requests
import re
from bs4 import BeautifulSoup
import csv
import os

app = Flask(__name__)

url = "https://en.wikipedia.org/wiki/Lists_of_NBA_players"

def count(name):
    words = name.split()
    return sum(len(word) > 0 for word in words)

def get_player_info(player_name):
    player_info_url = f"https://en.wikipedia.org/wiki/{player_name.replace(' ', '_')}"
    
    try:
        response = requests.get(player_info_url)
        response.raise_for_status()
        content = response.content.decode('utf-8')

        soup = BeautifulSoup(content, 'html.parser')
        infobox = soup.find('table', class_='infobox')

        info_dict = {}
        if (infobox):
            for row in infobox.find_all('tr'):
                header = row.find('th')
                data = row.find('td')
                if header and data:
                    info_dict[header.text.strip()] = data.text.strip()
        else:
            info_dict["Info"] = "No information found"

        return info_dict
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching player info: {e}")
        return {"Error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/crawl_players', methods=['POST'])
def crawl_players():
    all_player_data = []

    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.content.decode('utf-8')

        subpage_pattern = r'href="(/wiki/List_of_National_Basketball_Association_players[^":#]+)"'
        subpage_links = re.findall(subpage_pattern, content)
        full_links = [f"https://en.wikipedia.org{link}" for link in subpage_links]

        for link in full_links:
            try:
                subpage_response = requests.get(link)
                subpage_response.raise_for_status()
                subpage_content = subpage_response.content.decode('utf-8')

                player_name_pattern = r'<li><a href="/wiki/[^"]+" title="([^"]+)">'
                player_names = re.findall(player_name_pattern, subpage_content)

                filter_names = [name for name in player_names if count(name) <= 4 and len(name.split()) > 1]
                
                for player_name in filter_names:
                    player_info = get_player_info(player_name)
                    all_player_data.append({
                        "name": player_name,
                        "info": player_info
                    })

                    if len(all_player_data) >= 200:
                        break

            except requests.exceptions.RequestException as e:
                print(f"Error accessing {link}: {e}")
                continue

        unique_player_data = {player['name']: player for player in all_player_data}
        limited_player_data = list(unique_player_data.values())[:200]

        csv_filename = 'nba_players.csv'
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'info']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for player in limited_player_data:
                if isinstance(player['info'], dict):
                    player_info_str = "; ".join([f"{key}: {value}" for key, value in player['info'].items()])
                else:
                    player_info_str = "No information found"

                writer.writerow({
                    'name': player['name'],
                    'info': player_info_str
                })

        return render_template('player_list.html', players=[player['name'] for player in limited_player_data])

    except requests.exceptions.RequestException as e:
        print(f"Error fetching main page: {e}")
        return render_template('index.html', error=str(e))

@app.route('/download_csv')
def download_csv():
    csv_path = os.path.join(os.getcwd(), 'nba_players.csv')
    if os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True, mimetype='text/csv')
    else:
        return "File not found.", 404

@app.route('/player/<name>', methods=['GET'])
def player_info(name):
    player_info_url = f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}"
    
    try:
        response = requests.get(player_info_url)
        response.raise_for_status()
        content = response.content.decode('utf-8')

        soup = BeautifulSoup(content, 'html.parser')
        infobox = soup.find('table', class_='infobox')

        if infobox:
            info_dict = {}
            for row in infobox.find_all('tr'):
                header = row.find('th')
                data = row.find('td')
                if header and data:
                    info_dict[header.text.strip()] = data.text.strip()

            info_html = '<table class="infobox">'
            for key, value in info_dict.items():
                info_html += f'<tr><th>{key}</th><td>{value}</td></tr>'
            info_html += '</table>'
        else:
            info_html = "Not found"

        return render_template('player_info.html', name=name, info=info_html)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching player info: {e}")
        return render_template('player_info.html', name=name, info="Not found")
    
if __name__ == '__main__':
    app.run(debug=True)
