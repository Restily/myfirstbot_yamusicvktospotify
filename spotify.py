#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vk_api
import base64
from vk_api import audio
import json
import requests
from secrettokens import client_64, login, password, Token
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import keyboards as kb


#captcha
def captcha_handler(captcha):
    key = input("Enter captcha code {0}: ".format(captcha.get_url())).strip()

    # Пробуем снова отправить запрос с капчей
    return captcha.try_again(key)

#login vk
def login_vk(login,password):
    vk_session = vk_api.VkApi(
        login, password,
        captcha_handler=captcha_handler  # функция для обработки капчи
    )
    try:
        vk_session.auth()
        return vk_session   
    except vk_api.AuthError as error_msg:
        print(error_msg)
        return


def get_vk_songs(vk_session,user_id):
    vk_audio = audio.VkAudio(vk_session)
    songs = vk_audio.get(user_id)
    try:
        songs = vk_audio.get(user_id)
        return songs   
    except (vk_api.exceptions.AccessDenied, ValueError) as error:
        songs = 'Введен неверный id, либо профиль или аудиозаписи пользователя закрыты\nПроверьте id и настройки приватности и попробуйте ещё раз.'
        return songs

def get_yandex_songs(user_id):
    r = requests.get('https://music.yandex.ru/users/{}/tracks'.format(user_id))

    #получение артистов
    page = r.text
    dart = 'd-track__artists'
    deco = 'deco-link'
    lend = len(deco)
    arts = []
    while dart in page:
        p = 0
        artist = ''
        ind = page.index(dart)
        page = page[ind:]
        kekw = page.index('</div>')
        artists = page[:kekw]
        while deco in artists:
            if p!=0:
                artist +=', '
            ind = artists.index(deco)
            artists = artists[ind+2+lend:]
            for ind,el in enumerate(artists):
                if el == '<':
                    page = page[ind+2+lend+ind:]
                    break
                else:
                    artist += el
            p += 1
        if ' ' in artist:
            a = artist.split()
            for ind, el in enumerate(a):
                if '#' in el:
                    del a[ind]
                    break
            if len(a) == 1:
                ark = a[0]
                if ark[len(ark)-1:] == ',':
                    a[0] = ark[:len(ark)-1]
            artist = ' '.join(a)
        arts.append(artist)

    #получение названий
    page = r.text
    dart = 'd-track__name'
    deco = 'title='
    alph = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz'
    lend = len(deco)
    tits = []
    while dart in page:
        p = 0
        title = ''
        ind = page.index(dart)
        page = page[ind:]
        kekw = page.index('</div>')
        titles = page[:kekw]
        while deco in titles:
            if p!=0:
                title +=' '
            ind = titles.index(deco)
            titles = titles[ind+1+lend:]
            for ind,el in enumerate(titles):
                if el == '>' or el == 'М':
                    page = page[ind+2+lend+ind:]
                    break
                else:
                    title += el
            p += 1
        if ' ' in title:
            a = title.split()
            for ind, el in enumerate(a):
                if '#' in el:
                    del a[ind]
                    break
                if '.' in el:
                    a = a[:ind]
            if len(a) == 1:
                ark = a[0]
                if ark[:-1] == ',':
                    a[0] = ark[:len(ark)-1]
            title = ' '.join(a)
        if title[-1] not in alph:
            title = title[:-1]
        tits.append(title)

    songs = []
    for i in range(len(tits)):
        songs.append({'artist': arts[i], 'title': tits[i]})
    if songs == []:
        songs = 'Введен неверный логин.\nПроверьте логин и попробуйте ещё раз.'
    return songs

class CreatePlaylist:   
    def __init__(self):
        pass

    def create_playlist(self, user_id):
        
        #узнаем айди юзера

        query = 'https://api.spotify.com/v1/me'
        response = requests.get(
            query,
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(access_token)
            }
        )

        response_json = response.json()
        spotify_user_id = response_json['uri'][13:]

        #создание нового плейлиста

        request_body = json.dumps({
            "name": "Аудиозаписи юзера {}".format(user_id),
            "description": "Создано при помощи бота @vktospotify (t.me/vktospotify_bot)",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            spotify_user_id)

        response = requests.post(
            query,
            data = request_body,
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(access_token)
            }
        )
        
        response_json = response.json()

        # айди плейлиста
        return response_json["id"]

    def get_spotify_uri(self, artist, song_name):
        
        #поиск песни в spotify
        
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(access_token)
            }
        )
        
        response_json = response.json()
        
        songsg = response_json["tracks"]["items"]
        

        for hh in songsg:
            return hh['uri']
    

    def add_song_to_playlist(self, user_id, platforma):    
        # создание нового плейлиста
        if platforma == 'vk':
            global session
            songs = get_vk_songs(session, user_id)
            if songs == 'Введен неверный id, либо профиль или аудиозаписи пользователя закрыты\nПроверьте id и настройки приватности и попробуйте ещё раз.':
                nosearch = []
                return songs, nosearch
        elif platforma == 'ya':
            songs = get_yandex_songs(user_id)
            if songs == 'Введен неверный логин.\nПроверьте логин и попробуйте ещё раз.':
                nosearch = []
                return songs, nosearch
        
        playlist_id = self.create_playlist(user_id)
        allsongs = len(songs)
        
        #работа со списком музыки
        for song in songs:
            a = song['artist'].split()
            if 'feat.' in a:
                a.remove('feat.')
            if 'x' in a: 
                a.remove('x')
            if 'х' in a:
                a.remove('х')
            song['artist'] = ' '.join(a)
            
            a = song['title'].split()
            for ind,el in enumerate(a):
                p = []
                q = 0
                lenel = len(el)
                lena = len(a)
                for c in range(lenel):
                    if el[c].isupper():
                        p.append(c)
                        q += 1
                if q == 2:
                    ing = p[1]
                    a[ind] = el[:ing] + ' ' + el[ing:]
                if '(' in el:
                    for cool in range(ind,lena):
                        if cool<lena:
                            a[cool] = ''
                if '[' in el:
                    for cool in range(ind,lena):
                        if cool<lena:
                            a[cool] = ''
                if 'prod' in el:
                    for cool in range(ind,lena):
                        if cool<lena:
                            a[cool] = ''
                if 'feat' in el:
                    for kool in range(ind,lena):
                        a[kool] = ''
            song['title'] = ' '.join(a)
                    
        
        # сборка юри
        def obrabot(songs, qp):
            bled = ''
            kek = qp
            uris = []
            nosearch = []
            for song in songs:
                ret = self.get_spotify_uri(song['artist'],song['title'])
                if ret == None:
                    a = song['artist'].split()
                    bled = a
                    song['artist'] = a[0]
                    ret2 = self.get_spotify_uri(song['artist'],song['title'])
                    if ret2 == None:
                        song['artist'] = ' '.join(bled)
                        nosearch.append(song)
                else:
                    uris.append(ret)
                qp += 1
                if qp - kek == 40:
                    return uris, qp, nosearch
            return uris, qp, nosearch
        
        qp = 0
        notsearch = []
        # добавить песни в новый плейлист
        while qp != allsongs:
            uris, qp, nosearch = obrabot(songs[qp:], qp)
            alluris = []
            for el in uris:
                if el not in alluris:
                    alluris.append(el)
                else:
                    uris.remove(el)
            if nosearch != []:
                for song in nosearch:
                    if (song['artist'] not in notsearch) and (song['title'] not in notsearch):
                        notsearch.append(song['artist'])
                        notsearch.append(song['title'])
            request_data = json.dumps(uris)
        
            query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
                playlist_id)
        
            response = requests.post(
                query,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer {}".format(access_token)
                }
            )

            response.json()
        
        return 'open.spotify.com/playlist/{}'.format(playlist_id), notsearch

access_token = ''
schet = 0
authHeader = {}
authData = {}

def get_tokens(code):
    authUrl = 'https://accounts.spotify.com/api/token'
    authHeader['Authorization'] = "Basic " + client_64
    authData['grant_type'] = "authorization_code"
    authData['code'] = code
    authData['redirect_uri'] = 'https://open.spotify.com/'

    res = requests.post(authUrl, headers=authHeader, data=authData)
    
    response = res.json()
    global access_token
    try:
        access_token = response['access_token']
    except KeyError:
        return 'Проверьте ссылку и попробуйте ещё раз.'

#телеграм бот
API_TOKEN = Token


#логгинг
logging.basicConfig(level=logging.INFO)


#инициализация бота
bot = Bot(token=API_TOKEN)
memory_storage = MemoryStorage()
dp = Dispatcher(bot, storage=memory_storage)

# телеграм бот
class Blyat(StatesGroup):
    vk = State()
    yandex = State()

@dp.message_handler(commands = ['start'])
async def send_welcome(message: types.Message):
    await message.answer('Привет! Это бот для импорта музыки из Vk в Spotify.\nНажмите на кнопку ниже, чтобы начать импорт.\n\nБот создан на основе vk_api и spotify_api.\n\nСоздатель: @Restily', reply_markup = kb.greet_kb)

@dp.message_handler(lambda message: message.text == 'Создать новый плейлист')
async def vk_to_spotify_again(message: types.Message):
    await message.answer('1) Авторизуйся в своём аккаунте Spotify по этой ссылке: https://tinyurl.com/vktospotifybot\n(Если вы уже авторизаны, переходите к следующему шагу)\n2) Отправьте мне url (ссылку) страницы. (Вы должны оказаться на сайте open.spotify.com)\n\nВ дальнейшем вы можете запретить доступ приложению к вашему аккаунту по ссылке: https://www.spotify.com/ru-ru/account/apps/\n\nЕсли вы с мобильного устройства, нажмите на иконку в правом верхнем углу -> Копировать ссылку', reply_markup = kb.ReplyKeyboardRemove())

@dp.message_handler(lambda message: 'open.spotify.com' in message.text)
async def get_platfrom(message: types.Message):
    code = message.text[31:]
    lolkek = get_tokens(code)
    if lolkek == 'Проверьте ссылку и попробуйте ещё раз.':
        await message.answer(lolkek)
    else:
        await message.answer('Выберите платформу, с которой планируете импортировать музыку', reply_markup = kb.greet_vars)

@dp.message_handler(lambda message: message.text == 'Назад')
async def back(message: types.Message):   
    await message.answer('Выберите платформу, с которой планируете импортировать музыку', reply_markup = kb.greet_vars)

@dp.message_handler(lambda message: message.text == 'VK')
async def get_vk_id(message: types.Message):
    await message.answer('Введи id страницы, с которой хочешь импортировать музыку.\nПолучить id можно здесь: https://regvk.com/id/.\nАудиозаписи и профиль должны быть открытыми.', reply_markup = kb.greet_back)
    await Blyat.vk.set()

@dp.message_handler(lambda message: message.text == 'Yandex.Музыка')
async def get_ya_id(message: types.Message):
    await message.answer('Перейдите на https://passport.yandex.ru/profile, скопируйте логин под своей аватаркой (он должен быть на английском языке) и отправьте боту', reply_markup = kb.greet_back)
    await Blyat.yandex.set()

@dp.message_handler(state=Blyat.vk)
async def vk_to_spotify(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await back(message)
        await state.finish()
        return
    user_id = message.text
    cp = CreatePlaylist()
    await message.answer('Создание плейлиста может занять несколько минут.\nБот пришлёт ссылку на плейлист после импорта.')
    url, nosearch = cp.add_song_to_playlist(user_id,'vk')
    if url == 'Введен неверный id, либо профиль или аудиозаписи пользователя закрыты\nПроверьте id и настройки приватности и попробуйте ещё раз.':
        await message.answer(url)
        await state.finish()
        return None
    else:
        kek = 'Ссылка на плейлист: {}'.format(str(url))
    spis = []
    qeq = len(nosearch)
    a = ''
    for i in range(0,qeq-1,2):
        a += '\n' + nosearch[i] + ' - ' + nosearch[i+1]
        if i%10==0 and i!=0:
            spis.append(a)
            a = ''
    global schet
    schet += 1
    await message.answer(kek)
    for ind,spisn in enumerate(spis):
        if ind==0:
            await message.answer('Не удалось загрузить песни:{}'.format(spisn))
        else:
            await message.answer(spisn)
    await message.answer('Чтобы создать ещё один плейлист, нажмите кнопку ниже.', reply_markup=kb.greet_kb)
    await state.finish()

@dp.message_handler(state=Blyat.yandex)
async def ya_to_spotify(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await back(message)
        await state.finish()
        return
    user_id = message.text
    cp = CreatePlaylist()
    await message.answer('Создание плейлиста может занять несколько минут.\nБот пришлёт ссылку на плейлист после импорта.')
    url, nosearch = cp.add_song_to_playlist(user_id, 'ya')
    if url == 'Введен неверный логин.\nПроверьте логин и попробуйте ещё раз.':
        await message.answer(url)
        return None
    else:
        kek = 'Ссылка на плейлист: {}'.format(str(url))
    spis = []
    qeq = len(nosearch)
    a = ''
    for i in range(0,qeq-1,2):
        a += '\n' + nosearch[i] + ' - ' + nosearch[i+1]
        if i == qeq-2 and i%10!=0:
            spis.append(a)
        if i%10==0 and i!=0:
            spis.append(a)
            a = ''
    global schet
    schet += 1
    await message.answer(kek)
    for ind,spisn in enumerate(spis):
        if ind==0:
            await message.answer('Не удалось загрузить песни:{}'.format(spisn))
        else:
            await message.answer(spisn)
    await message.answer('Чтобы создать ещё один плейлист, нажмите кнопку ниже.', reply_markup=kb.greet_kb)
    await state.finish()


@dp.message_handler(commands = ['playlists'])
async def schetchik(message: types.Message):
    await message.answer("За всё время бот @vktospotify_bot создал плейлистов: {}".format(schet))

@dp.message_handler()
async def error_dolbaeba(message: types.Message):
    await message.answer('Вы отправили не то, что нужно. Проверьте и попробуйте ещё раз.', reply_markup=kb.greet_kb)

if __name__ == '__main__':
    session = login_vk(login,password)
    executor.start_polling(dp, skip_updates=True)
