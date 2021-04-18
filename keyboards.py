from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

btnplay = KeyboardButton('Создать новый плейлист')
greet_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(btnplay)
