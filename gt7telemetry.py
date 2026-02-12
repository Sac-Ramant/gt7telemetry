import signal
from datetime import datetime as dt
from datetime import timedelta as td
import socket
import sys
import struct
from Crypto.Cipher import Salsa20
import json

# ansi prefix
pref = "\033["

# ports for send and receive data
SendPort = 33739
ReceivePort = 33740

# ctrl-c handler
def handler(signum, frame):
    sys.stdout.write(f'{pref}?1049l')    # revert buffer
    sys.stdout.write(f'{pref}?25h')        # restore cursor
    sys.stdout.flush()
    exit(1)

# handle ctrl-c
signal.signal(signal.SIGINT, handler)

sys.stdout.write(f'{pref}?1049h')    # alt buffer
sys.stdout.write(f'{pref}?25l')        # hide cursor
sys.stdout.flush()

# get ip address from command line
if len(sys.argv) == 2:
    ip = sys.argv[1]
else:
    print('Run like : python3 gt7telemetry.py <playstation-ip>')
    exit(1)

# Create a UDP socket, bind it et bridge
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', ReceivePort))
s.settimeout(10)
out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
NEXUS_ADDR = ("127.0.0.1", 9999)

# data stream decoding
def salsa20_dec(dat):
    KEY = b'Simulator Interface Packet GT7 ver 0.0'
    # Seed IV is always located here
    oiv = dat[0x40:0x44]
    iv1 = int.from_bytes(oiv, byteorder='little')
    # Notice DEADBEAF, not DEADBEEF
    iv2 = iv1 ^ 0xDEADBEAF
    IV = bytearray()
    IV.extend(iv2.to_bytes(4, 'little'))
    IV.extend(iv1.to_bytes(4, 'little'))
    
    cipher = Salsa20.new(key=KEY[0:32], nonce=bytes(IV))
    ddata = cipher.decrypt(dat)
    
    magic = int.from_bytes(ddata[0:4], byteorder='little')
    if magic != 0x47375330:
        return bytearray(b'')
    return ddata

# send heartbeat
def send_hb(s):
    send_data = 'A'
    s.sendto(send_data.encode('utf-8'), (ip, SendPort))

# generic print function
def printAt(str, row=1, column=1, bold=0, underline=0, reverse=0):
    sys.stdout.write('{}{};{}H'.format(pref, row, column))
    if reverse:
        sys.stdout.write('{}7m'.format(pref))
    if bold:
        sys.stdout.write('{}1m'.format(pref))
    if underline:
        sys.stdout.write('{}4m'.format(pref))
    if not bold and not underline and not reverse:
        sys.stdout.write('{}0m'.format(pref))
    sys.stdout.write(str)

def secondsToLaptime(seconds):
    minutes = seconds // 60
    remaining = seconds % 60
    return '{:01.0f}:{:06.3f}'.format(minutes, remaining)

# start by sending heartbeat
send_hb(s)

printAt('GT7 Telemetry Display 0.7 (ctrl-c to quit)', 1, 1, bold=1)
printAt('Packet ID:', 1, 73)

# Initialisation barre ligne 2
printAt('{:<92}'.format(''), 2, 1, reverse=1)

printAt('{:<92}'.format('Current Track Data'), 3, 1, reverse=1, bold=1)
printAt('Time on track:', 3, 41, reverse=1)
printAt('Laps:    /', 5, 1)
printAt('Position:   /', 5, 21)
printAt('Best Lap Time:', 7, 1)
printAt('Current Lap Time: ', 7, 31)
printAt('Last Lap Time:', 8, 1)

printAt('{:<92}'.format('Current Car Data'), 10, 1, reverse=1, bold=1)
printAt('Car ID:', 10, 41, reverse=1)
printAt('Throttle:    %', 12, 1)
printAt('RPM:         rpm', 12, 21)
printAt('Speed:        kph', 12, 41)
printAt('Brake:        %', 13, 1)
printAt('Gear:   ( )', 13, 21)
printAt('Boost:        kPa', 13, 41)
printAt('Rev Warning       rpm', 12, 71)
printAt('Rev Limiter       rpm', 13, 71)
printAt('Max:', 14, 21)
printAt('Est. Speed        kph', 14, 71)

printAt('Clutch:        /', 15, 1)
printAt('RPM After Clutch:        rpm', 15, 31)

printAt('Oil Temperature:       °C', 17, 1)
printAt('Water Temperature:       °C', 17, 31)
printAt('Oil Pressure:          bar', 18, 1)
printAt('Body/Ride Height:        mm', 18, 31)

printAt('Tyre Data', 20, 1, underline=1)
printAt('FL:        °C', 21, 1)
printAt('FR:        °C', 21, 21)
printAt('ø:      /       cm', 21, 41)
printAt('           kph', 22, 1)
printAt('           kph', 22, 21)
printAt('Δ:      /       ', 22, 41)
printAt('RL:        °C', 25, 1)
printAt('RR:        °C', 25, 21)
printAt('ø:      /       cm', 25, 41)
printAt('           kph', 26, 1)
printAt('           kph', 26, 21)
printAt('Δ:      /       ', 26, 41)

printAt('Gearing', 29, 1, underline=1)
printAt('1st:', 30, 1)
printAt('2nd:', 31, 1)
printAt('3rd:', 32, 1)
printAt('4th:', 33, 1)
printAt('5th:', 34, 1)
printAt('6th:', 35, 1)
printAt('7th:', 36, 1)
printAt('8th:', 37, 1)
printAt('FNL:', 39, 1)

printAt('Positioning (m)', 29, 21, underline=1)
printAt('X:', 30, 21)
printAt('Y:', 31, 21)
printAt('Z:', 32, 21)

printAt('Velocity (m/s)', 29, 41, underline=1)
printAt('X:', 30, 41)
printAt('Y:', 31, 41)
printAt('Z:', 32, 41)

printAt('Rotation', 34, 21, underline=1)
printAt('P:', 35, 21)
printAt('Y:', 36, 21)
printAt('R:', 37, 21)

printAt('Angular (r/s)', 34, 41, underline=1)
printAt('X:', 35, 41)
printAt('Y:', 36, 41)
printAt('Z:', 37, 41)

printAt('N/S:', 39, 21)

sys.stdout.flush()

prevlap = -1
pktid = 0
pknt = 0
prev_pkt_time = -1

while True:
    try:
        data, address = s.recvfrom(4096)
        pknt = pknt + 1
        ddata = salsa20_dec(data)
# --- ENVOI AU NEXUS ---
        if len(ddata) > 0:
            # --- CALCUL DES ÉTATS (CONTEXTE) ---
            tick = struct.unpack('i', ddata[0x80:0x80+4])[0]
            flags = struct.unpack('H', ddata[0x8E:0x8E+2])[0]
            curlap = struct.unpack('h', ddata[0x74:0x74+2])[0]
            tot_laps = struct.unpack('h', ddata[0x76:0x76+2])[0]
            new_pktid = struct.unpack('i', ddata[0x70:0x70+4])[0]
            
            paused = (flags & 2)
            in_race = (flags & 1)
            # Condition stricte pour la télémétrie active
            is_session_course = (tick > 0) and (0 < curlap <= (tot_laps if tot_laps > 0 else 999)) and (new_pktid > 0)

            # --- LOGIQUE DU PONT (BRIDGE) ---
            if paused or not in_race:
                game_status = "PAUSE_OR_MENU"
                tele_data = None  # On vide la data pour forcer l'IA à regarder l'image du menu
            elif not is_session_course:
                game_status = "FINISHED_OR_REPLAY"
                tele_data = None
            else:
                game_status = "IN_RACE"
                # On ne peuple 'data' que si on est vraiment en piste
                tele_data = {
                    "pos": {
                        "x": struct.unpack('f', ddata[0x04:0x04+4])[0],
                        "y": struct.unpack('f', ddata[0x08:0x08+4])[0],
                        "z": struct.unpack('f', ddata[0x0C:0x0C+4])[0]
                    },
                    "rot": {
                        "pitch": struct.unpack('f', ddata[0x10:0x10+4])[0],
                        "yaw": struct.unpack('f', ddata[0x14:0x14+4])[0],
                        "roll": struct.unpack('f', ddata[0x18:0x18+4])[0]
                    },
                    "speed": round(struct.unpack('f', ddata[0x4C:0x4C+4])[0] * 3.6, 1),
                    "throttle": round(struct.unpack('B', ddata[0x91:0x91+1])[0] / 2.55),
                    "gear": struct.unpack('B', ddata[0x90:0x90+1])[0] & 0x0F
                }

            # Envoi du paquet structuré
            packet_to_nexus = {
                "status": game_status,
                "data": tele_data
            }
            
            try:
                out_sock.sendto(json.dumps(packet_to_nexus).encode(), NEXUS_ADDR)
            except Exception:
                pass
            new_pktid = struct.unpack('i', ddata[0x70:0x70+4])[0]
            if new_pktid > pktid:
                pktid = new_pktid

                # --- 1. EXTRACTION DES DONNÉES (On récupère tout ici) ---
                bstlap = struct.unpack('i', ddata[0x78:0x78+4])[0]
                lstlap = struct.unpack('i', ddata[0x7C:0x7C+4])[0]
                curlap = struct.unpack('h', ddata[0x74:0x74+2])[0]
                tot_laps = struct.unpack('h', ddata[0x76:0x76+2])[0]
                tick = struct.unpack('i', ddata[0x80:0x80+4])[0]
                flags = struct.unpack('H', ddata[0x8E:0x8E+2])[0]

                # --- 2. LOGIQUE DE LA BANNIÈRE INTELLIGENTE ---
                paused = (flags & 2)
                in_race = (flags & 1)
                time_frozen = (tick == prev_pkt_time)
                
                # Tes 3 conditions pour "EN COURSE"
                is_session_course = (tick > 0) and (0 < curlap <= (tot_laps if tot_laps > 0 else 999)) and (new_pktid > 0)

                if paused or not in_race:
                    status = "\033[41m   PAUSE / MENU   \033[0m"
                elif curlap < 1:
                    status = "\033[42m GRILLE DE DÉPART \033[0m"
                elif tot_laps > 0 and curlap > tot_laps:
                    status = "\033[41m  COURSE TERMINÉE \033[0m"
                elif time_frozen and tick > 0:
                    status = "\033[41m SIMULATION FIGÉE \033[0m"
                elif is_session_course:
                    status = "\033[42m    EN COURSE     \033[0m"
                else:
                    status = "\033[44m    EN ATTENTE    \033[0m"
                
                # Affichage de la bannière sur la ligne 2
                printAt(f"{status:^92}", 2, 1, bold=1)
                prev_pkt_time = tick

                # --- 3. TON CALCUL DE CHRONO (Inchangé) ---
                if curlap > 0:
                    if curlap != prevlap:
                        prevlap = curlap
                        tick_start = tick
                    
                    curLapTime_ms = tick - tick_start
                    if curLapTime_ms < 0: curLapTime_ms = 0 # Sécurité si reset
                    printAt('{:>9}'.format(secondsToLaptime(curLapTime_ms / 1000)), 7, 49)
                else:
                    printAt('{:>9}'.format(''), 7, 49)
                        
                cgear = struct.unpack('B', ddata[0x90:0x90+1])[0] & 0b00001111
                sgear = struct.unpack('B', ddata[0x90:0x90+1])[0] >> 4
                if cgear < 1:
                    cgear = 'R'
                if sgear > 14:
                    sgear = '–'

                fuelCapacity = struct.unpack('f', ddata[0x48:0x48+4])[0]
                isEV = False if fuelCapacity > 0 else True
                if isEV:
                    printAt('Charge:', 14, 1)
                    printAt('{:3.0f} kWh'.format(struct.unpack('f', ddata[0x44:0x44+4])[0]), 14, 11)
                    printAt('??? kWh', 14, 29)
                else:
                    printAt('Fuel:  ', 14, 1)
                    printAt('{:3.0f} lit'.format(struct.unpack('f', ddata[0x44:0x44+4])[0]), 14, 11)
                    printAt('{:3.0f} lit'.format(struct.unpack('f', ddata[0x48:0x48+4])[0]), 14, 29)

                boost = struct.unpack('f', ddata[0x50:0x50+4])[0] - 1
                hasTurbo = True if boost > -1 else False

                tyreDiamFL = struct.unpack('f', ddata[0xB4:0xB4+4])[0]
                tyreDiamFR = struct.unpack('f', ddata[0xB8:0xB8+4])[0]
                tyreDiamRL = struct.unpack('f', ddata[0xBC:0xBC+4])[0]
                tyreDiamRR = struct.unpack('f', ddata[0xC0:0xC0+4])[0]

                tyreSpeedFL = abs(3.6 * tyreDiamFL * struct.unpack('f', ddata[0xA4:0xA4+4])[0])
                tyreSpeedFR = abs(3.6 * tyreDiamFR * struct.unpack('f', ddata[0xA8:0xA8+4])[0])
                tyreSpeedRL = abs(3.6 * tyreDiamRL * struct.unpack('f', ddata[0xAC:0xAC+4])[0])
                tyreSpeedRR = abs(3.6 * tyreDiamRR * struct.unpack('f', ddata[0xB0:0xB0+4])[0])

                carSpeed = 3.6 * struct.unpack('f', ddata[0x4C:0x4C+4])[0]

                if carSpeed > 0:
                    tyreSlipRatioFL = '{:6.2f}'.format(tyreSpeedFL / carSpeed)
                    tyreSlipRatioFR = '{:6.2f}'.format(tyreSpeedFR / carSpeed)
                    tyreSlipRatioRL = '{:6.2f}'.format(tyreSpeedRL / carSpeed)
                    tyreSlipRatioRR = '{:6.2f}'.format(tyreSpeedRR / carSpeed)
                else:
                    tyreSlipRatioFL = tyreSlipRatioFR = tyreSlipRatioRL = tyreSlipRatioRR = '  –  '

                printAt('{:>8}'.format(str(td(seconds=round(tick / 1000)))), 3, 56, reverse=1)

                printAt('{:3.0f}'.format(curlap), 5, 7)
                printAt('{:3.0f}'.format(struct.unpack('h', ddata[0x76:0x76+2])[0]), 5, 11)

                printAt('{:2.0f}'.format(struct.unpack('h', ddata[0x84:0x84+2])[0]), 5, 31)
                printAt('{:2.0f}'.format(struct.unpack('h', ddata[0x86:0x86+2])[0]), 5, 34)

                if bstlap != -1:
                    printAt('{:>9}'.format(secondsToLaptime(bstlap / 1000)), 7, 16)
                else:
                    printAt('{:>9}'.format(''), 7, 16)
                if lstlap != -1:
                    printAt('{:>9}'.format(secondsToLaptime(lstlap / 1000)), 8, 16)
                else:
                    printAt('{:>9}'.format(''), 8, 16)

                printAt('{:5.0f}'.format(struct.unpack('i', ddata[0x124:0x124+4])[0]), 10, 48, reverse=1)

                printAt('{:3.0f}'.format(struct.unpack('B', ddata[0x91:0x91+1])[0] / 2.55), 12, 11)
                printAt('{:7.0f}'.format(struct.unpack('f', ddata[0x3C:0x3C+4])[0]), 12, 25)
                printAt('{:7.1f}'.format(carSpeed), 12, 47)
                printAt('{:5.0f}'.format(struct.unpack('H', ddata[0x88:0x88+2])[0]), 12, 83)

                printAt('{:3.0f}'.format(struct.unpack('B', ddata[0x92:0x92+1])[0] / 2.55), 13, 11)
                printAt('{}'.format(cgear), 13, 27)
                printAt('{}'.format(sgear), 13, 30)

                if hasTurbo:
                    printAt('{:7.2f}'.format(struct.unpack('f', ddata[0x50:0x50+4])[0] - 1), 13, 47)
                else:
                    printAt('{:>7}'.format('–'), 13, 47)

                printAt('{:5.0f}'.format(struct.unpack('H', ddata[0x8A:0x8A+2])[0]), 13, 83)
                printAt('{:5.0f}'.format(struct.unpack('h', ddata[0x8C:0x8C+2])[0]), 14, 83)

                printAt('{:5.3f}'.format(struct.unpack('f', ddata[0xF4:0xF4+4])[0]), 15, 9)
                printAt('{:5.3f}'.format(struct.unpack('f', ddata[0xF8:0xF8+4])[0]), 15, 17)
                printAt('{:7.0f}'.format(struct.unpack('f', ddata[0xFC:0xFC+4])[0]), 15, 48)

                printAt('{:6.1f}'.format(struct.unpack('f', ddata[0x5C:0x5C+4])[0]), 17, 17)
                printAt('{:6.1f}'.format(struct.unpack('f', ddata[0x58:0x58+4])[0]), 17, 49)

                printAt('{:6.2f}'.format(struct.unpack('f', ddata[0x54:0x54+4])[0]), 18, 17)
                printAt('{:6.0f}'.format(1000 * struct.unpack('f', ddata[0x38:0x38+4])[0]), 18, 49)

                printAt('{:6.1f}'.format(struct.unpack('f', ddata[0x60:0x60+4])[0]), 21, 5)
                printAt('{:6.1f}'.format(struct.unpack('f', ddata[0x64:0x64+4])[0]), 21, 25)
                printAt('{:6.1f}'.format(200 * tyreDiamFL), 21, 43)
                printAt('{:6.1f}'.format(200 * tyreDiamFR), 21, 50)

                printAt('{:6.1f}'.format(tyreSpeedFL), 22, 5)
                printAt('{:6.1f}'.format(tyreSpeedFR), 22, 25)
                printAt(tyreSlipRatioFL, 22, 43)
                printAt(tyreSlipRatioFR, 22, 50)

                printAt('{:6.3f}'.format(struct.unpack('f', ddata[0xC4:0xC4+4])[0]), 23, 5)
                printAt('{:6.3f}'.format(struct.unpack('f', ddata[0xC8:0xC8+4])[0]), 23, 25)

                printAt('{:6.1f}'.format(struct.unpack('f', ddata[0x68:0x68+4])[0]), 25, 5)
                printAt('{:6.1f}'.format(struct.unpack('f', ddata[0x6C:0x6C+4])[0]), 25, 25)
                printAt('{:6.1f}'.format(200 * tyreDiamRL), 25, 43)
                printAt('{:6.1f}'.format(200 * tyreDiamRR), 25, 50)

                printAt('{:6.1f}'.format(tyreSpeedRL), 26, 5)
                printAt('{:6.1f}'.format(tyreSpeedRR), 26, 25)
                printAt(tyreSlipRatioRL, 26, 43)
                printAt(tyreSlipRatioRR, 26, 50)

                printAt('{:6.3f}'.format(struct.unpack('f', ddata[0xCC:0xCC+4])[0]), 27, 5)
                printAt('{:6.3f}'.format(struct.unpack('f', ddata[0xD0:0xD0+4])[0]), 27, 25)

                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x104:0x104+4])[0]), 30, 5)
                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x108:0x108+4])[0]), 31, 5)
                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x10C:0x10C+4])[0]), 32, 5)
                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x110:0x110+4])[0]), 33, 5)
                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x114:0x114+4])[0]), 34, 5)
                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x118:0x118+4])[0]), 35, 5)
                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x11C:0x11C+4])[0]), 36, 5)
                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x120:0x120+4])[0]), 37, 5)

                printAt('{:7.3f}'.format(struct.unpack('f', ddata[0x100:0x100+4])[0]), 39, 5)

                printAt('{:11.4f}'.format(struct.unpack('f', ddata[0x04:0x04+4])[0]), 30, 23)
                printAt('{:11.4f}'.format(struct.unpack('f', ddata[0x08:0x08+4])[0]), 31, 23)
                printAt('{:11.4f}'.format(struct.unpack('f', ddata[0x0C:0x0C+4])[0]), 32, 23)

                printAt('{:11.4f}'.format(struct.unpack('f', ddata[0x10:0x10+4])[0]), 30, 43)
                printAt('{:11.4f}'.format(struct.unpack('f', ddata[0x14:0x14+4])[0]), 31, 43)
                printAt('{:11.4f}'.format(struct.unpack('f', ddata[0x18:0x18+4])[0]), 32, 43)

                printAt('{:9.4f}'.format(struct.unpack('f', ddata[0x1C:0x1C+4])[0]), 35, 23)
                printAt('{:9.4f}'.format(struct.unpack('f', ddata[0x20:0x20+4])[0]), 36, 23)
                printAt('{:9.4f}'.format(struct.unpack('f', ddata[0x24:0x24+4])[0]), 37, 23)

                printAt('{:9.4f}'.format(struct.unpack('f', ddata[0x2C:0x2C+4])[0]), 35, 43)
                printAt('{:9.4f}'.format(struct.unpack('f', ddata[0x30:0x30+4])[0]), 36, 43)
                printAt('{:9.4f}'.format(struct.unpack('f', ddata[0x34:0x34+4])[0]), 37, 43)

                printAt('{:7.4f}'.format(struct.unpack('f', ddata[0x28:0x28+4])[0]), 39, 25)

                printAt('{:>10}'.format(pktid), 1, 83)

        if pknt > 100:
            send_hb(s)
            pknt = 0
    except Exception as e:
        printAt('Exception: {}'.format(e), 41, 1, reverse=1)
        send_hb(s)
        pknt = 0
        pass

    sys.stdout.flush()
