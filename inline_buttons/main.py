from dotenv import load_dotenv
load_dotenv()

import os
API_KEY = os.getenv('API_KEY')

import telebot

# inline buttons
from telebot.types import InlineKeyboardMarkup # to create the button panel
from telebot.types import InlineKeyboardButton # to create inline buttons

import requests
from bs4 import BeautifulSoup
import pickle

bot = telebot.TeleBot(API_KEY)

N_RES_PAG = 15
MAX_ANCHO_ROW = 8
DIR = {'busquedas': './busquedas'}
for key in DIR:
    try:
        os.mkdir(key)
    except:
        pass

# responds to the /panel command
@bot.message_handler(commands=['panel'])
def cmd_panel(message):
    """Shows a message with inline buttons (after the message)"""
    panel = InlineKeyboardMarkup(row_width=2)
    b1 = InlineKeyboardButton('Vlada Novikova', url='https://www.instagram.com/__nvkv21_/')
    b2 = InlineKeyboardButton('Vika Zabelskaya', url='https://www.instagram.com/vika.zabelskaya/')
    b3 = InlineKeyboardButton('Send song', callback_data='laura')
    b4 = InlineKeyboardButton('cerrar', callback_data='cerrar')
    
    panel.add(b1, b2, b3, b4)
    bot.send_message(message.chat.id, "Mis canales de ofertas.", reply_markup=panel)


@bot.callback_query_handler(func=lambda x : True)
def inline_buttons_response(call):
    """Gestiona las acciones de los botones callback_data"""
    cid = call.from_user.id # chat id del mensaje
    mid = call.message.id # mensaje id 

    if call.data == 'laura':
        video = open(os.path.join(os.path.abspath(os.curdir), 'video.mp4'), 'rb')
        print(video)
        bot.send_chat_action(cid, 'upload_video')
        bot.send_video(cid, video, '*Tra te e il mare*', parse_mode='MarkdownV2')
        return
    
    if call.data == 'cerrar':
        print('cerrar')
        bot.delete_message(cid, mid)
        return 
    datos = pickle.load(open(f'{DIR["busquedas"]}{cid}_{mid}', 'rb'))
    if call.data == 'anterior':
        if datos['pag'] == 0:
            bot.answer_callback_query(call.id, "Ya estás en la primera página.")
        else:
            datos['pag'] -= 1
            pickle.dump(datos, open(f'{DIR["busquedas"]}{cid}_{mid}', 'wb'))
            mostrar_pagina(datos['lista'], cid, datos['pag'], mid)
        return
    elif call.data == 'siguiente':
        if datos['pag'] * N_RES_PAG + N_RES_PAG >= len(datos['lista']):
            bot.answer_callback_query(call.id, "Ya estás en la última página")
        else:
            datos['pag'] += 1
            pickle.dump(datos, open(f'{DIR["busquedas"]}{cid}_{mid}', 'wb'))
            mostrar_pagina(datos['lista'], cid, datos['pag'], mid)
        return


@bot.message_handler(commands=['buscar'])
def cmd_buscar(message):
    """Realiza una busqueda en Google y devuelve una lista de listas de los resultados
    con la siguiente estructure [[titulo, url], [titulo, url]...]."""
    texto_buscar = " ".join(message.text.split()[1:])
    # si no se han pasado parámetros
    if not texto_buscar:
        texto = "Debes introducir una búsqueda. \n"
        texto += "Ejemplo:\n"
        texto += f'<code>{message.text} Vika Zabelskaya</code>'
        bot.send_message(message.chat.id, texto, parse_mode="html")
        return 1
    else:
        print(f'Buscando en Google: "{texto_buscar}"')
        url = f'https://www.google.com/search?q={texto_buscar.replace(" ", "+")}&num=100'
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        headers = {'user-agent' : user_agent}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f'ERROR al buscar: {res.status_code} {res.reason}')
            bot.send_message(message.chat.id, "Se ha producido un error. Inténtalo más tarde")
            return 1
        else:
            soup = BeautifulSoup(res.text, 'html.parser')
            elementos = soup.find_all('div', class_='g')
            lista = []
            for elemento in elementos:
                try:
                    titulo = elemento.find('h3').text
                    url = elemento.find('a').attrs.get('href')
                    if not url.startswith('http'):
                        url = 'https://google.com' + url
                    if [titulo, url] in lista:
                        continue
                    lista.append([titulo, url])
                except:
                    continue
        mostrar_pagina(lista, message.chat.id)

def mostrar_pagina(lista, cid, pag=0, mid=None):
    """Crea o edita un mensaje de la página."""
    left_hand = "U+1F448"
    right_hand = "U+1F449"
    close = "U+274C"
    left_hand = chr(int(left_hand.lstrip("U+"), 16))
    right_hand = chr(int(right_hand.lstrip("U+"), 16))
    close_icon = chr(int(close.lstrip("U+"), 16))
    markup = InlineKeyboardMarkup(row_width=MAX_ANCHO_ROW)
    b_anterior = InlineKeyboardButton(left_hand, callback_data="anterior")
    b_cerrar = InlineKeyboardButton(close_icon, callback_data="cerrar")
    b_siguiente = InlineKeyboardButton(right_hand, callback_data="siguiente")
    inicio = pag * N_RES_PAG
    fin = pag*N_RES_PAG + N_RES_PAG
    if fin > len(lista):
        fin = len(lista)
    mensaje = f'<i>Resultados {inicio + 1}-{fin} de {len(lista)}</i>\n\n'
    n=1
    botones = []
    for item in lista[inicio:fin]:
        botones.append(InlineKeyboardButton(str(n), url=item[1]))
        mensaje+=f'[<b>{n}</b>]<a href="{item[1]}">{item[0]}</a>\n'
        n += 1
    markup.add(*botones)
    markup.row(b_anterior, b_cerrar, b_siguiente)


    if mid:
        bot.edit_message_text(mensaje, cid, mid, reply_markup=markup, parse_mode='html', disable_web_page_preview=True)
    else:
        res = bot.send_message(cid, mensaje, reply_markup=markup, parse_mode='html', disable_web_page_preview=True)
        mid = res.message_id
        datos = {'pag':0, 'lista':lista}
        pickle.dump(datos, open(f'{DIR["busquedas"]}{cid}_{mid}', 'wb'))
    
if __name__ == '__main__':
    print("Iniciando el bot")
    bot.infinity_polling()