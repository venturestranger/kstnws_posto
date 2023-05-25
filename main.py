import telebot
from telebot import types
from datetime import datetime as dt
import requests
from config import Config

post = {
	"title": "",
	"lead": "",
	"content": "",
	"id_author": 0,
	"picture_url": "",
	"date_publication": "",
	"date_edit": "",
	"hashtags": "",
	"category": ""
}

shared = {}
bot = telebot.TeleBot(Config.TELEGRAM_TOKEN)

def stop_check(message):
	if message.text != None and message.text.startswith("/stop"):
		bot.send_message(message.chat.id, "Генерация остановлена")
		return True
	else:
		return False

def menu():
	keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)

	keyboard.add(types.InlineKeyboardButton("/status"))
	keyboard.add(types.InlineKeyboardButton("/upload"))
	keyboard.add(types.InlineKeyboardButton("/codes"))

	return keyboard

def process():
	keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)

	keyboard.add(types.InlineKeyboardButton("/stop"))

	return keyboard

def request(method, endpoint, json=None, data=None):
	headers = {
		"Content-Type": "application/json" if json != None else "image/jpeg",
		"Authorization": "Bearer " + Config.API_TOKEN
	}
	if method.lower() == 'get':
		return requests.get(Config.URL + endpoint, json=json, data=data, headers=headers)
	elif method.lower() == 'post':
		return requests.post(Config.URL + endpoint, json=json, data=data, headers=headers)
	elif method.lower() == 'put':
		return requests.put(Config.URL + endpoint, json=json, data=data, headers=headers)

@bot.message_handler(commands=['status'])
def help_handler(message):
	bot.send_message(message.chat.id, "200", reply_markup=menu())

@bot.message_handler(commands=['codes'])
def help_handler(message):
	bot.send_message(message.chat.id, """Статус коды:
	1. 200 ОК
	2. 400 Плохой запрос (неправильный формат отправленного файла или неправильное обращение к серверу)
	3. 401 Не авторизован (неправильный ключ доступа у бота)
	4. 404 Не найден (не найден ресурс на сервере)
	5. 405 Метод не разрешен
	6. 500 Внутренняя ошибка сервера
	7. 502 Сервер не предоставил точку доступа
	""", reply_markup=menu())

@bot.message_handler(commands=['upload'])
def upload_post_handler(message):
	shared[message.chat.id] = post.copy()
	bot.send_message(message.chat.id, "Отправить название поста",  reply_markup=process())
	bot.register_next_step_handler(message, title_handler)

def title_handler(message):
	if stop_check(message):
		return
	else:
		shared[message.chat.id]["title"] = message.text
		bot.send_message(message.chat.id, "Отправить наполнение поста", reply_markup=process())
		bot.register_next_step_handler(message, content_handler)

def content_handler(message):
	if stop_check(message):
		return
	else:
		shared[message.chat.id]["content"] = message.text
		bot.send_message(message.chat.id, "Отправить хэштэги поста (каждое новое слово - новый хэштэг)", reply_markup=process())
		bot.register_next_step_handler(message, hashtags_handler)

def hashtags_handler(message):
	if stop_check(message):
		return
	else:
		shared[message.chat.id]["hashtags"] = message.text

		keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
		resp = request('get', '/api/rest/categories')

		for item in resp.json():
			keyboard.add(types.InlineKeyboardButton(item["name"]))
		keyboard.add(types.InlineKeyboardButton("/stop"))

		bot.send_message(message.chat.id, "Выбрать категорию поста", reply_markup=keyboard)
		bot.register_next_step_handler(message, category_handler)

def category_handler(message):
	if stop_check(message):
		return
	else:
		shared[message.chat.id]["category"] = message.text
		bot.send_message(message.chat.id, "Отправить изображение поста", reply_markup=process())
		bot.register_next_step_handler(message, send_to_server_handler)

def send_to_server_handler(message):
	if stop_check(message):
		return
	else:
		try:
			file_id = None
			if message.document != None:
				file_id = message.document.file_id
			else:
				file_id = message.photo[-1].file_id
			file_info = bot.get_file(file_id)
			downloaded_file = bot.download_file(file_info.file_path)
		except Exception as e:
			bot.send_message(message.chat.id,
				"Ошибка при сохранении изображения, попробуйте еще раз")
		else:
			bot.send_message(message.chat.id, "Связываемся с сервером")
			resp = request('post', '/asset/upload', data=downloaded_file)
			bot.send_message(message.chat.id, f"Статус сохранения изображения {resp.status_code}", reply_markup=menu())
			print(resp)

			shared[message.chat.id]["picture_url"] = "$am1:" + resp.content.decode("utf-8")
			shared[message.chat.id]["date_publication"] = shared[message.chat.id]["date_edit"] = str(dt.now())
			resp = request('post', '/validate', json=shared[message.chat.id]) 
			bot.send_message(message.chat.id, f"Статус сохранения поста {resp.status_code}", reply_markup=menu())
			print(resp)
			print("----")

if __name__=="__main__":
	print("Bot Has Been Started")
	bot.polling()
