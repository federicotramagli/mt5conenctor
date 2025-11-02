"""
MT5 Trading Server - Backend per MT5 Controller
Gestisce connessioni MetaTrader5 e esecuzione ordini multi-account
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import MetaTrader5 as mt5
from datetime import datetime
import logging
import os

app = Flask(__name__)
CORS(app)  # Permette richieste da qualsiasi origine

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dizionario per tenere traccia delle connessioni attive
active_connections = {}

# =====================================================
# ENDPOINT: Connetti a MT5
# =====================================================
@app.route('/api/mt5_connect', methods=['POST'])
def connect_mt5():
    """
    Connette un account MT5 e ritorna i dati dell'account
    Body: {account: int, password: str, server: str}
    """
    try:
        data = request.json
        account = int(data['account'])
        password = data['password']
        server = data['server']
        
        logger.info(f"Tentativo connessione account {account} su server {server}")
        
        # Inizializza MT5
        if not mt5.initialize():
            error = mt5.last_error()
            logger.error(f"MT5 initialization failed: {error}")
            return jsonify({
                'status': 'error',
                'error': f'MT5 initialization failed: {error}'
            }), 500
        
        # Login all'account
        authorized = mt5.login(account, password=password, server=server)
        
        if not authorized:
            error = mt5.last_error()
            logger.error(f"Login failed for account {account}: {error}")
            mt5.shutdown()
            return jsonify({
                'status': 'error',
                'error': f'Login failed: {error}'
            }), 401
        
        # Ottieni info account
        account_info = mt5.account_info()
        
        if account_info is None:
            logger.error("Failed to get account info")
            mt5.shutdown()
            return jsonify({
                'status': 'error',
                'error': 'Failed to get account info'
            }), 500
        
        # Salva connessione attiva
        active_connections[account] = {
            'server': server,
            'connected': True,
            'last_login': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Account {account} connesso con successo")
        
        return jsonify({
            'status': 'success',
            'account_number': str(account),
            'server': server,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'currency': account_info.currency,
            'leverage': account_info.leverage,
            'connection_status': 'connected',
            'message': 'Connesso con successo a MT5'
        })
        
    except Exception as e:
        logger.error(f"Error in connect_mt5: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# =====================================================
# ENDPOINT: Sincronizza dati account
# =====================================================
@app.route('/api/mt5_sync', methods=['POST'])
def sync_accounts():
    """
    Sincronizza dati di più account MT5
    Body: {accounts: [account_number1, account_number2, ...]}
    """
    try:
        data = request.json
        accounts = data['accounts']
        results = []
        
        for account_num in accounts:
            account = int(account_num)
            
            # Verifica se l'account è nelle connessioni attive
            if account in active_connections:
                # Ottieni info aggiornate
                account_info = mt5.account_info()
                
                if account_info and account_info.login == account:
                    results.append({
                        'account_number': account_num,
                        'balance': account_info.balance,
                        'equity': account_info.equity,
                        'currency': account_info.currency,
                        'margin': account_info.margin,
                        'margin_free': account_info.margin_free,
                        'connection_status': 'connected',
                        'last_update': datetime.now().isoformat()
                    })
                else:
                    results.append({
                        'account_number': account_num,
                        'connection_status': 'disconnected',
                        'last_update': datetime.now().isoformat()
                    })
            else:
                results.append({
                    'account_number': account_num,
                    'connection_status': 'disconnected',
                    'last_update': datetime.now().isoformat()
                })
        
        return jsonify({
            'status': 'success',
            'accounts': results,
            'sync_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in sync_accounts: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# =====================================================
# ENDPOINT: Esegui ordine manuale multi-account
# =====================================================
@app.route('/api/manual_execute', methods=['POST'])
def execute_manual_trade():
    """
    Esegue un ordine su più account contemporaneamente
    """
    try:
        data = request.json
        symbol = data['symbol']
        direction = data['direction']
        base_volume = float(data['base_volume'])
        tp = float(data['tp']) if data.get('tp') else None
        sl = float(data['sl']) if data.get('sl') else None
        accounts = data['accounts']
        
        execution_id = f"exec_{int(datetime.now().timestamp())}"
        results = []
        
        logger.info(f"🚀 Esecuzione ordine {execution_id}: {direction} {base_volume} {symbol}")
        
        # Determina il tipo di ordine
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        
        for acc_data in accounts:
            account = int(acc_data['account_number'])
            multiplier = float(acc_data['multiplier'])
            volume = round(base_volume * multiplier, 2)
            
            logger.info(f"  → Account {account}: volume {volume}")
            
            # Prepara la richiesta di ordine
            request_dict = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "deviation": 20,
                "magic": 234000,
                "comment": f"MT5Controller_{execution_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Aggiungi TP/SL se specificati
            if tp:
                request_dict['tp'] = tp
            if sl:
                request_dict['sl'] = sl
            
            # Invia l'ordine
            result = mt5.order_send(request_dict)
            
            if result is None:
                error = mt5.last_error()
                logger.error(f"  ❌ Errore account {account}: {error}")
                results.append({
                    'account_number': str(account),
                    'symbol': symbol,
                    'direction': direction,
                    'volume': volume,
                    'ticket': None,
                    'execution_price': None,
                    'status': 'REJECTED',
                    'error': str(error),
                    'timestamp': datetime.now().isoformat()
                })
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"  ❌ Account {account} rejected: {result.comment}")
                results.append({
                    'account_number': str(account),
                    'symbol': symbol,
                    'direction': direction,
                    'volume': volume,
                    'ticket': None,
                    'execution_price': None,
                    'status': 'REJECTED',
                    'error': result.comment,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.info(f"  ✅ Account {account}: ticket {result.order}")
                results.append({
                    'account_number': str(account),
                    'symbol': symbol,
                    'direction': direction,
                    'volume': volume,
                    'ticket': result.order,
                    'execution_price': result.price,
                    'status': 'FILLED',
                    'error': None,
                    'timestamp': datetime.now().isoformat()
                })
        
        return jsonify({
            'status': 'success',
            'execution_id': execution_id,
            'symbol': symbol,
            'direction': direction,
            'base_volume': base_volume,
            'tp': tp,
            'sl': sl,
            'results': results,
            'executed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in execute_manual_trade: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# =====================================================
# ENDPOINT: Health check
# =====================================================
@app.route('/health', methods=['GET'])
def health_check():
    """Health check per verificare che il server sia attivo"""
    mt5_status = "initialized" if mt5.initialize() else "not_initialized"
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'mt5_status': mt5_status,
        'active_connections': len(active_connections)
    })


# =====================================================
# Avvio server
# =====================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"🚀 Starting MT5 Trading Server on port {port}")
    logger.info("📡 CORS enabled for all origins")
    
    # Avvia il server
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True  # Cambia a False in produzione
    )
