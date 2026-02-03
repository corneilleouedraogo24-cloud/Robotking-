import ccxt
import time
import os

# ================== CONFIGURATION RÉELLE ==================
# COLLE TES CLÉS ENTRE LES GUILLEMETS CI-DESSOUS
API_KEY='YQL8N4sxGb6YF3RmfhaQIv2MMNuoB3AcQqf7x1YaVzARKoGb1TKjumwUVNZDW3af'
API_SECRET='si08ii320XMByW4VY1VRt5zRJNnB3QrYBJc3QkDOdKHLZGKxyTo5CHxz7nd4CuQ0'

SYMBOL = 'BTC/USDT'
SYMBOL_BINANCE = 'BTCUSDT'
RISK_PER_TRADE = 0.40  # Risque par trade en USDT
TRAILING_RATIO = 0.5   # Sensibilité du SL
FEE_MARGIN = 1.0       # Marge de sécurité
LEVERAGE = 20          # Levier pour capital de 5$

# Initialisation de la connexion Binance Futures
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
})

class SMCRunnerFinal:
    def __init__(self):
        self.active_order_id = None
        self.current_trade = None
        self.balance = 0
        try:
            # Force le levier x20 sur Binance
            exchange.fapiPrivate_post_leverage({'symbol': SYMBOL_BINANCE, 'leverage': LEVERAGE})
        except: pass

    def sync_binance_sl(self, side, sl_price, qty):
        """ Annule et remplace le Stop Loss réel sur Binance """
        if self.active_order_id:
            try: exchange.cancel_order(self.active_order_id, SYMBOL)
            except: pass
        
        sl_side = 'sell' if side == 'buy' else 'buy'
        try:
            # Ordre STOP_MARKET avec ReduceOnly pour protéger le capital
            params = {'stopPrice': round(sl_price, 2), 'reduceOnly': True}
            order = exchange.create_order(SYMBOL, 'STOP_MARKET', sl_side, qty, None, params)
            self.active_order_id = order['id']
        except Exception as e:
            print(f"⚠️ Erreur SL Binance: {e}")

    def run(self):
        print("🚀 SMC RUNNER : SYNC LIVE BINANCE DEMARRÉ")
        while True:
            try:
                # 1. Récupérer les données
                ticker = exchange.fetch_ticker(SYMBOL)
                price = ticker['last']
                ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1m', limit=15)
                vol = ohlcv[-1][2] - ohlcv[-1][3]
                
                # 2. Vérifier la position réelle sur Binance
                pos = exchange.fetch_positions([SYMBOL])
                real_qty = float(pos[0]['info']['positionAmt'])

                # Cas : Pas de position ouverte
                if real_qty == 0:
                    if self.current_trade:
                        print("🏁 Position clôturée (SL touché).")
                        self.current_trade = None
                        self.active_order_id = None
                    
                    # Détection de tendance (MA 12)
                    ma = sum([k[4] for k in ohlcv]) / len(ohlcv)
                    side = 'buy' if price > ma else 'sell'
                    
                    # Calcul de la taille (Money Management)
                    sl_dist = (TRAILING_RATIO * vol) + FEE_MARGIN
                    qty = max(round(RISK_PER_TRADE / sl_dist, 3), 0.002)
                    sl_price = price - sl_dist if side == 'buy' else price + sl_dist
                    
                    print(f"🔥 SIGNAL {side.upper()} | Qty: {qty} | SL: {sl_price:.2f}")
                    exchange.create_market_order(SYMBOL, side, qty)
                    self.current_trade = {'side': side, 'sl': sl_price, 'dist': sl_dist, 'qty': qty}
                    self.sync_binance_sl(side, sl_price, qty)

                # Cas : Position en cours (Trailing)
                else:
                    if self.current_trade:
                        old_sl = self.current_trade['sl']
                        # Suivi du prix pour remonter/descendre le SL
                        if self.current_trade['side'] == 'buy' and (price - self.current_trade['dist']) > old_sl:
                            self.current_trade['sl'] = price - self.current_trade['dist']
                            self.sync_binance_sl('buy', self.current_trade['sl'], self.current_trade['qty'])
                        elif self.current_trade['side'] == 'sell' and (price + self.current_trade['dist']) < old_sl:
                            self.current_trade['sl'] = price + self.current_trade['dist']
                            self.sync_binance_sl('sell', self.current_trade['sl'], self.current_trade['qty'])

                self.update_display(price)
                time.sleep(4) # Délai pour éviter le bannissement d'API

            except Exception as e:
                print(f"⚠️ Erreur: {e}")
                time.sleep(10)

    def update_display(self, price):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("==================================================")
        print(f"🚀 SMC RUNNER : ANDROID LIVE")
        print(f"BTC/USDT : {price:.2f}$")
        print("==================================================")
        if self.current_trade:
            print(f"STATUS : 🟢 TRADE {self.current_trade['side'].upper()}")
            print(f"SL SYNC : {self.current_trade['sl']:.2f}$")
        else:
            print("STATUS : 🔍 ANALYSE DU MARCHÉ...")
        print("==================================================")

if __name__ == "__main__":
    bot = SMCRunnerFinal()
    bot.run()
