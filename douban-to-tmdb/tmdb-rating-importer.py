import requests
import re

# 设置您的 TMDb API 密钥
api_key = 'your_api_key'

# 设置您的 TMDb 用户名和密码
username = 'your_username'
password = 'your_password'

# 获取会话 ID
session_id_url = f'https://api.themoviedb.org/3/authentication/token/new?api_key={api_key}'
response = requests.get(session_id_url)
request_token = response.json()['request_token']

validate_url = f'https://api.themoviedb.org/3/authentication/token/validate_with_login?api_key={api_key}&username={username}&password={password}&request_token={request_token}'
response = requests.get(validate_url)
request_token = response.json()['request_token']

session_id_url = f'https://api.themoviedb.org/3/authentication/session/new?api_key={api_key}&request_token={request_token}'
response = requests.get(session_id_url)
session_id = response.json()['session_id']

lines_to_remove = []
success_count = 0
failure_count = 0
skipped_count = 0

rated_shows = {}

# 从文件中读取影片评分数据并按标题分组
shows = {}
with open('ratings.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split(':')
        if len(parts) != 2:
            continue
        title, rating = parts
        title_parts = title.strip().split(' (')
        if len(title_parts) == 2:
            title, year = title_parts
            year = year[:-1]
        else:
            title = title.strip()
            year = None
        # 移除标题中的第x季或Season x
        title_cleaned = re.sub(r'(第.+季|Season\s*\d+)', '', title).strip()
        shows.setdefault(title_cleaned, []).append((line, int(rating.strip()), year))

# 计算平均评分和最早年份，并对电视剧分组进行处理
for show_title, show_data in shows.items():
    avg_rating = round(sum(x[1] for x in show_data) / len(show_data))
    min_year = min((x[2] for x in show_data if x[2]), default=None)

    # 搜索电影和电视剧
    search_movie_url = f'https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={show_title}&year={min_year}'
    search_tv_url = f'https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={show_title}&first_air_date_year={min_year}'
    response_movie = requests.get(search_movie_url)
    response_tv = requests.get(search_tv_url)
    results_movie = response_movie.json()['results']
    results_tv = response_tv.json()['results']
    results = results_movie + results_tv

    # 检查 results 列表是否为空
    if not results:
        failure_count += 1
        continue

    # 取匹配度最高的项目进行评分
    result = max(results, key=lambda x: x['popularity'])
    media_type = result['media_type'] if 'media_type' in result else ('tv' if result in results_tv else 'movie')
    media_id = result['id']

    # 检查该电视剧或电影是否已经评分过
    if media_id in rated_shows:
        continue

    # 添加评分信息
    rating_url = f'https://api.themoviedb.org/3/{media_type}/{media_id}/rating?api_key={api_key}&session_id={session_id}'
    data = {'value': avg_rating * 2}
    response = requests.post(rating_url, json=data)
    
    if response.status_code == 201:
        print(f'Successfully rated {show_title} as {avg_rating}')
        success_count += 1
        rated_shows[media_id] = True
        
        # 删除已成功评分的行并更新文档
        with open('ratings.txt', 'r', encoding='utf-8') as f:
            lines_to_remove.extend([x[0] for x in show_data])
            lines_to_keep=[line for line in f if line not in lines_to_remove]
        with open('ratings.txt', 'w', encoding='utf-8') as f:
            f.writelines(lines_to_keep)
    else:
        failure_count += 1

    # 统计跳过的数量（电视剧分组内季数减一之和）
    seasons_count = len(show_data)
    if seasons_count > 1:  
        skipped_count += seasons_count - 1

# 打印统计信息
print()
print(f'Total rated: {success_count}')
print(f'Total failed: {failure_count}')
print(f'Total skipped: {skipped_count}')
