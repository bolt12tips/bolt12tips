import asyncio
import obspython as obs
import websockets
import json
import qrcode

from typing import Optional

import threading

def script_description():
  return """<center><h2>Bolt-12 Tips!!</h2></center>
            <p>When you receive a <em>Bolt-12</em> tip the cat takes them and shows you the note.</p>"""

def script_properties():
	# Create a Property Set object
    props = obs.obs_properties_create()
    
    # password can be found in .phoenix/phoenix.conf
    obs.obs_properties_add_text(props, 'password', 'http-password-limited-access:', obs.OBS_TEXT_DEFAULT)
    
    # shown when you run phoenix
    obs.obs_properties_add_text(props, 'lno', 'bolt-12 offer:', obs.OBS_TEXT_DEFAULT)

    return props

def update_settings(settings):
    global data
    global uri
    global password
    global lno
    data = settings
    password = obs.obs_data_get_string(data, 'password')
    lno = obs.obs_data_get_string(data, 'lno')
    uri = f"ws://a:{password}@127.0.0.1:9740/websocket"
    qr = f"bitcoin:?lno={lno}"
    # save qr code to png file
    bolt12qrcode = qrcode.make(qr)
    bolt12qrcode.save(script_path()+"bolt12qrcode.png")

def script_load(settings):
    update_settings(settings)
        
    global _THREAD
    _THREAD = threading.Thread(None, run_stuff, daemon=True)
    _THREAD.start()

def script_update(settings):
    update_settings(settings)

    global _THREAD
    print("script_update:",_LOOP)
    if _LOOP is not None:
        _LOOP.call_soon_threadsafe(lambda l: l.stop(), _LOOP)

    if _THREAD is not None:
        # Wait for 5 seconds, if it doesn't exit just move on not to block
        # OBS main thread. Logging something about the failure to properly exit
        # is advised.
        _THREAD.join(timeout=5)
        _THREAD = None

def script_unload():
    global _THREAD
    print("script_unload:",_LOOP)
    if _LOOP is not None:
        _LOOP.call_soon_threadsafe(lambda l: l.stop(), _LOOP)

    if _THREAD is not None:
        # Wait for 5 seconds, if it doesn't exit just move on not to block
        # OBS main thread. Logging something about the failure to properly exit
        # is advised.
        _THREAD.join(timeout=5)
        _THREAD = None

def script_save(settings):
	obs.obs_data_set_string(settings, 'password', password)
	obs.obs_data_set_string(settings, 'lno', lno)

async def listen():
    async for websocket in websockets.connect(uri):
        try:
            print(f"Connected!")
            async for message in websocket:
                data = json.loads(message)
                print(f"Received: {message}")
                cat_item = get_sceneitem_from_source_name_in_current_scene("cat")
                amount_note_item = get_sceneitem_from_source_name_in_current_scene("received")
                if cat_item is not None:
                    obs.obs_sceneitem_set_visible(cat_item, True)
                amount_note_item = get_sceneitem_from_source_name_in_current_scene("received")
                if amount_note_item is not None:
                    obs.obs_sceneitem_set_visible(amount_note_item, True)
                    amount_note_source = obs.obs_get_source_by_name("received")
                    if amount_note_source is not None:
                        settings = obs.obs_data_create()
                        if 'payerNote' in data:
                            obs.obs_data_set_string(settings, "text", f"{data['amountSat']} sats: {data['payerNote']}")
                        else:
                            obs.obs_data_set_string(settings, "text", f"{data['amountSat']} sats")
                        obs.obs_source_update(amount_note_source, settings)
                        obs.obs_data_release(settings)
                play_sound("game-start-6104.mp3")
                await asyncio.sleep(5)
                if cat_item is not None:
                    obs.obs_sceneitem_set_visible(cat_item, False)
                amount_note_item = get_sceneitem_from_source_name_in_current_scene("received")
                if amount_note_item is not None:
                    obs.obs_sceneitem_set_visible(amount_note_item, False)
                
                
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection Closed!")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            print(f"Unhandled exception: {e}")
            await asyncio.sleep(5)
            continue

_LOOP: Optional[asyncio.AbstractEventLoop] = None
_THREAD: Optional[threading.Thread] = None

def run_stuff():
    _LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(_LOOP)

    print("Async waiting for websocket to recv data.")
    asyncio.run(listen())

    # Stop anything that is running on the loop before closing. Most likely
    # using the loop run_until_complete function
    _LOOP.close()
    _LOOP = None

# Retrieves the scene item of the given source name in the current scene or None if not found
def get_sceneitem_from_source_name_in_current_scene(name):
  result_sceneitem = None
  current_scene_as_source = obs.obs_frontend_get_current_scene()
  if current_scene_as_source:
    current_scene = obs.obs_scene_from_source(current_scene_as_source)
    result_sceneitem = obs.obs_scene_find_source_recursive(current_scene, name)
    obs.obs_source_release(current_scene_as_source)
  return result_sceneitem
    

media_source = None
outputIndex = 63  # Last index

def play_sound(filename):
    media_source = obs.obs_source_create_private(
        "ffmpeg_source", "Global Media Source", None
    )
    mp3_data = obs.obs_data_create()
    print("play_cound: " + script_path() + filename)
    obs.obs_data_set_string(mp3_data, "local_file", script_path() + filename)
    obs.obs_source_update(media_source, mp3_data)
    obs.obs_source_set_monitoring_type(
        media_source, obs.OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT
    )
    obs.obs_data_release(mp3_data)
    obs.obs_set_output_source(outputIndex, media_source)
    obs.obs_source_release(media_source)    

