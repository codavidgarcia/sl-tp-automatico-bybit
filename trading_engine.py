import time
import threading
from pybit.unified_trading import HTTP
from decimal import Decimal, ROUND_FLOOR
from typing import Optional, Dict, Any, List
import queue


class TradingEngine:
    """Motor de trading unificado que combina funcionalidad de Stop Loss y Take Profit"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.session = None
        self.running = False
        self.thread = None
        
        # Trading state
        self.symbol = ''
        self.stop_loss_enabled = False
        self.take_profit_enabled = False
        self.stop_loss_amount = 0
        self.take_profit_percentage = 0
        self.position_mode = None

        # Internal state
        self.position_capital = 0
        self.position_price = 0
        self.position_size = 0
        self.take_profit_order_id = ''

        # Communication
        self.log_queue = queue.Queue()
        self.status_callback = None
        self.last_time_check = 0

    def check_time_sync(self) -> bool:
        """Check if local time is synchronized with Bybit server time"""
        try:
            # Get Bybit server time
            server_time_response = self.session.get_server_time()
            server_time = int(server_time_response['result']['timeSecond'])

            # Get local time
            local_time = int(time.time())

            # Calculate difference
            time_diff = abs(server_time - local_time)

            self.log(f"⏰ Diferencia de tiempo: {time_diff} segundos")

            if time_diff > 30:
                self.log(f"⚠️ ADVERTENCIA: Reloj desincronizado ({time_diff}s)")
                self.log("💡 Recomendación: Sincronizar reloj del sistema")
                return False
            elif time_diff > 10:
                self.log(f"⚠️ Diferencia de tiempo notable: {time_diff}s")
                return True
            else:
                self.log(f"✅ Tiempo sincronizado correctamente")
                return True

        except Exception as e:
            self.log(f"❌ Error verificando sincronización: {e}")
            return True

    def initialize_session(self) -> bool:
        """Initialize Bybit session with time sync check"""
        try:
            self.session = HTTP(
                testnet=self.testnet,
                api_key=self.api_key,
                api_secret=self.api_secret,
                recv_window=60000,  # 60 seconds window to handle clock drift
            )

            # Check time synchronization
            self.check_time_sync()

            # Test connection
            self.session.get_wallet_balance(accountType="UNIFIED")
            self.log("Sesión inicializada exitosamente")
            return True
        except Exception as e:
            self.log(f"Falló al inicializar sesión: {e}")
            # If it's a timestamp error, provide specific guidance
            if "timestamp" in str(e).lower() or "time" in str(e).lower():
                self.log("🕐 Error de tiempo detectado")
                self.log("💡 Solución: Sincronizar reloj del sistema")
                self.log("   • Windows: Configuración > Hora e idioma > Sincronizar")
                self.log("   • macOS: Preferencias > Fecha y hora > Automático")
                self.log("   • Linux: sudo ntpdate -s time.nist.gov")
            return False
    
    def log(self, message: str):
        """Add message to log queue"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")
    
    def qty_step(self, symbol: str, price: float) -> float:
        """Calculate proper price step for the symbol (preserved from original)"""
        try:
            step = self.session.get_instruments_info(category="linear", symbol=symbol)
            ticksize = float(step['result']['list'][0]['priceFilter']['tickSize'])
            scala_precio = int(step['result']['list'][0]['priceScale'])
            precision = Decimal(f"{10**scala_precio}")
            tickdec = Decimal(f"{ticksize}")
            precio_final = (Decimal(f"{price}") * precision) / precision
            precide = precio_final.quantize(Decimal(f"{1/precision}"), rounding=ROUND_FLOOR)
            operaciondec = (precide / tickdec).quantize(Decimal('1'), rounding=ROUND_FLOOR) * tickdec
            result = float(operaciondec)
            return result
        except Exception as e:
            self.log(f"Error calculando paso de precio: {e}")
            return price

    def get_min_order_qty(self, symbol: str) -> float:
        """Get minimum order quantity for symbol"""
        try:
            instruments = self.session.get_instruments_info(category="linear", symbol=symbol)
            if instruments.get('retCode') == 0 and instruments['result']['list']:
                min_qty = float(instruments['result']['list'][0]['lotSizeFilter']['minOrderQty'])
                self.log(f"Cantidad mínima de orden para {symbol}: {min_qty}")
                return min_qty
            return 0.001  # Default fallback
        except Exception as e:
            self.log(f"Error obteniendo cantidad mínima de orden: {e}")
            return 0.001

    def set_stop_loss(self, symbol: str, price: float) -> bool:
        """Establecer orden de stop loss con detección automática de modo de posición"""
        try:
            price = self.qty_step(symbol, price)

            # Check if stop loss already exists at this price
            position_info = self.get_position_info(symbol)
            if position_info:
                current_sl = position_info.get('stopLoss', '')
                if current_sl and abs(float(current_sl) - price) < 0.01:
                    self.log(f"Stop loss ya establecido en {current_sl}, omitiendo")
                    return True

            self.log(f"Setting stop loss at {price}")

            # Detect position mode automatically
            position_idx = self.detect_position_mode(symbol)

            order = self.session.set_trading_stop(
                category="linear",
                symbol=symbol,
                stopLoss=price,
                slTriggerB="LastPrice",
                positionIdx=position_idx,
            )

            # If it fails with position mode error, try other modes
            if order.get('retCode') == 10001:
                self.log("Modo de posición no coincide, probando modos alternativos...")

                # Try all possible position indices
                for idx in [0, 1, 2]:
                    if idx != position_idx:
                        self.log(f"Trying position index {idx}")
                        order = self.session.set_trading_stop(
                            category="linear",
                            symbol=symbol,
                            stopLoss=price,
                            slTriggerB="LastPrice",
                            positionIdx=idx,
                        )
                        if order.get('retCode') == 0:
                            self.position_mode = idx  # Update detected mode
                            break

            if order.get('retCode') == 0:
                self.log("Stop loss establecido exitosamente")
                return True
            elif order.get('retCode') == 34040:
                self.log("Stop loss already configured at this price")
                return True  # Consider this a success
            else:
                self.log(f"Falló al establecer stop loss: {order.get('retMsg', 'Error desconocido')}")
                return False

        except Exception as e:
            error_msg = str(e).lower()
            if "timestamp" in error_msg or "time" in error_msg or "recv_window" in error_msg:
                self.log(f"🕐 Error de sincronización al configurar SL: {e}")
                self.log("💡 Verificando sincronización de tiempo...")
                self.check_time_sync()
                return False
            else:
                self.log(f"Error estableciendo stop loss: {e}")
                return False
    
    def cancel_take_profit_order(self, symbol: str, order_id: str) -> bool:
        """Cancel existing take profit order"""
        try:
            self.log("Cancelling take profit order")
            order = self.session.cancel_order(
                category="linear",
                symbol=symbol,
                orderId=order_id,
            )
            return order.get('retCode') == 0
        except Exception as e:
            self.log(f"Error cancelando take profit: {e}")
            return False

    def cancel_all_tp_orders(self, symbol: str) -> bool:
        """Cancel ALL existing TP orders for exclusive control"""
        try:
            self.log("🧹 Cancelando TODAS las órdenes TP existentes para control exclusivo...")

            # Get all open orders for this symbol
            orders = self.session.get_open_orders(category="linear", symbol=symbol)

            if orders.get('retCode') != 0:
                self.log(f"Error obteniendo órdenes: {orders.get('retMsg', 'Error desconocido')}")
                return False

            tp_orders_cancelled = 0
            order_list = orders.get('result', {}).get('list', [])

            for order in order_list:
                # Identify TP orders (Limit orders with reduceOnly=True)
                if (order.get('orderType') == 'Limit' and
                    order.get('reduceOnly') == True):

                    order_id = order.get('orderId')
                    order_price = order.get('price')
                    order_qty = order.get('qty')

                    self.log(f"🎯 TP detectado: ID={order_id}, Precio=${order_price}, Qty={order_qty}")

                    # Cancel this TP order
                    cancel_result = self.session.cancel_order(
                        category="linear",
                        symbol=symbol,
                        orderId=order_id
                    )

                    if cancel_result.get('retCode') == 0:
                        tp_orders_cancelled += 1
                        self.log(f"✅ TP cancelado: ${order_price}")
                    else:
                        self.log(f"⚠️ Error cancelando TP {order_id}: {cancel_result.get('retMsg')}")

            if tp_orders_cancelled > 0:
                self.log(f"🧹 {tp_orders_cancelled} órdenes TP manuales canceladas - control exclusivo establecido")
            else:
                self.log("✅ No se encontraron órdenes TP existentes")

            return True

        except Exception as e:
            self.log(f"❌ Error cancelando órdenes TP: {e}")
            return False
    
    def set_take_profit(self, symbol: str, price: float, side: str, qty: float) -> Optional[str]:
        """Establecer orden de take profit con detección automática de modo de posición"""
        try:
            price = self.qty_step(symbol, price)

            # Ensure quantity meets minimum requirements
            min_qty = self.get_min_order_qty(symbol)
            if qty < min_qty:
                self.log(f"Quantity {qty} is below minimum {min_qty}, adjusting")
                qty = min_qty

            self.log(f"Setting take profit at {price} with quantity {qty}")

            # Reverse side for closing position
            order_side = 'Sell' if side == 'Buy' else 'Buy'

            # Detect position mode automatically
            position_idx = self.detect_position_mode(symbol)

            # For hedge mode, determine correct position index based on original side
            if position_idx in [1, 2]:
                position_idx = 1 if side == 'Buy' else 2

            order = self.session.place_order(
                category="linear",
                symbol=symbol,
                side=order_side,
                orderType="Limit",
                reduceOnly=True,
                qty=str(qty),
                price=str(price),
                positionIdx=position_idx,
            )

            # If it fails with position mode error, try other modes
            if order.get('retCode') == 10001:
                self.log("Modo de posición no coincide, probando modos alternativos...")

                # Try all possible position indices
                for idx in [0, 1, 2]:
                    if idx != position_idx:
                        self.log(f"Trying position index {idx}")
                        order = self.session.place_order(
                            category="linear",
                            symbol=symbol,
                            side=order_side,
                            orderType="Limit",
                            reduceOnly=True,
                            qty=str(qty),
                            price=str(price),
                            positionIdx=idx,
                        )
                        if order.get('retCode') == 0:
                            self.position_mode = idx  # Update detected mode
                            break

            if order.get('retCode') == 0:
                order_id = order['result']['orderId']
                self.log(f"Take profit establecido exitosamente: {order_id}")
                return order_id
            else:
                self.log(f"Falló al establecer take profit: {order.get('retMsg', 'Error desconocido')}")
                return None

        except Exception as e:
            self.log(f"Error estableciendo take profit: {e}")
            return None

    def set_take_profit_with_trading_stop(self, symbol: str, price: float) -> bool:
        """Set take profit using trading stop (similar to stop loss) for real-time updates"""
        try:
            price = self.qty_step(symbol, price)

            # Check if take profit already exists at this price
            position_info = self.get_position_info(symbol)
            if position_info:
                current_tp = position_info.get('takeProfit', '')
                if current_tp and abs(float(current_tp) - price) < 0.01:
                    self.log(f"Take profit ya establecido en {current_tp}, omitiendo")
                    return True

            self.log(f"Setting take profit at {price}")

            # Detect position mode automatically
            position_idx = self.detect_position_mode(symbol)

            order = self.session.set_trading_stop(
                category="linear",
                symbol=symbol,
                takeProfit=price,
                tpTriggerBy="LastPrice",
                positionIdx=position_idx,
            )

            # If it fails with position mode error, try other modes
            if order.get('retCode') == 10001:
                self.log("Modo de posición no coincide, probando modos alternativos...")

                # Try all possible position indices
                for idx in [0, 1, 2]:
                    if idx != position_idx:
                        self.log(f"Trying position index {idx}")
                        order = self.session.set_trading_stop(
                            category="linear",
                            symbol=symbol,
                            takeProfit=price,
                            tpTriggerBy="LastPrice",
                            positionIdx=idx,
                        )
                        if order.get('retCode') == 0:
                            self.position_mode = idx  # Update detected mode
                            break

            if order.get('retCode') == 0:
                self.log("Take profit establecido exitosamente")
                return True
            elif order.get('retCode') == 34040:
                self.log("Take profit already configured at this price")
                return True  # Consider this a success
            else:
                self.log(f"Falló al establecer take profit: {order.get('retMsg', 'Error desconocido')}")
                return False

        except Exception as e:
            self.log(f"Error setting take profit: {e}")
            return False

    def get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current position information"""
        try:
            positions = self.session.get_positions(category="linear", symbol=symbol)
            if positions.get('retCode') == 0 and positions['result']['list']:
                return positions['result']['list'][0]
            return None
        except Exception as e:
            self.log(f"Error obteniendo información de posición: {e}")
            return None

    def detect_position_mode(self, symbol: str) -> int:
        """Detect position mode for a symbol (0=one-way, 1=hedge-buy, 2=hedge-sell)"""
        if self.position_mode is not None:
            return self.position_mode

        try:
            # Try to get position info to detect mode
            positions = self.session.get_positions(category="linear", symbol=symbol)
            if positions.get('retCode') == 0 and positions['result']['list']:
                for pos in positions['result']['list']:
                    pos_idx = pos.get('positionIdx', 0)
                    if pos_idx in [1, 2]:  # Hedge mode
                        self.position_mode = pos_idx
                        self.log(f"Detected hedge mode, position index: {pos_idx}")
                        return pos_idx

            # Default to one-way mode
            self.position_mode = 0
            self.log("Detected one-way position mode")
            return 0

        except Exception as e:
            self.log(f"Error detectando modo de posición: {e}")
            self.position_mode = 0
            return 0

    def get_all_positions(self, category: str = "linear", settle_coin: str = "USDT") -> List[Dict[str, Any]]:
        """Get all current positions for a specific settlement coin"""
        try:
            # Ensure session is initialized
            if not self.session:
                self.log("Session not initialized, attempting to initialize...")
                if not self.initialize_session():
                    self.log("Failed to initialize session for position query")
                    return []

            # Use settleCoin parameter as required by Bybit API v5
            positions = self.session.get_positions(category=category, settleCoin=settle_coin)
            self.log(f"Raw positions response for {settle_coin}: retCode={positions.get('retCode')}")

            if positions.get('retCode') == 0:
                all_positions = positions['result']['list']
                self.log(f"Total positions returned: {len(all_positions)}")

                # Filter only positions with size > 0
                active_positions = []
                for pos in all_positions:
                    size = pos.get('size', '0')
                    symbol = pos.get('symbol', 'Unknown')
                    side = pos.get('side', 'None')

                    self.log(f"Position {symbol}: size={size}, side={side}")

                    # Check if position has actual size (could be string or float)
                    try:
                        size_float = float(size)
                        position_value = float(pos.get('positionValue', '0'))
                        unrealized_pnl = float(pos.get('unrealisedPnl', '0'))

                        # Consider position active if it has size, value, or PnL
                        if size_float != 0 or position_value != 0 or unrealized_pnl != 0:
                            active_positions.append(pos)
                            self.log(f"Added active position: {symbol} size={size_float} value={position_value} pnl={unrealized_pnl}")
                    except (ValueError, TypeError):
                        self.log(f"Invalid size format for {symbol}: {size}")

                self.log(f"Active positions found: {len(active_positions)}")
                return active_positions
            else:
                self.log(f"Error de API: {positions.get('retMsg', 'Error desconocido')}")
                return []
        except Exception as e:
            self.log(f"Error obteniendo todas las posiciones: {e}")
            return []

    def get_positions_summary(self) -> Dict[str, Any]:
        """Get a summary of all positions"""
        try:
            # Get positions for different settlement coins
            usdt_positions = self.get_all_positions("linear", "USDT")
            usdc_positions = self.get_all_positions("linear", "USDC")

            # Combine all positions
            linear_positions = usdt_positions + usdc_positions

            summary = {
                'total_positions': len(linear_positions),
                'total_unrealized_pnl': 0.0,
                'total_position_value': 0.0,
                'positions': []
            }

            for pos in linear_positions:
                position_data = {
                    'symbol': pos.get('symbol', ''),
                    'side': pos.get('side', ''),
                    'size': float(pos.get('size', 0)),
                    'entry_price': float(pos.get('avgPrice', 0)),
                    'mark_price': float(pos.get('markPrice', 0)),
                    'unrealized_pnl': float(pos.get('unrealisedPnl', 0)),
                    'position_value': float(pos.get('positionValue', 0)),
                    'leverage': pos.get('leverage', ''),
                    'position_status': pos.get('positionStatus', ''),
                    'auto_add_margin': pos.get('autoAddMargin', 0),
                    'position_idx': pos.get('positionIdx', 0),
                    'risk_id': pos.get('riskId', 0),
                    'risk_limit_value': pos.get('riskLimitValue', ''),
                    'trade_mode': pos.get('tradeMode', 0),
                    'position_balance': float(pos.get('positionBalance', 0)),
                    'liq_price': pos.get('liqPrice', ''),
                    'bust_price': pos.get('bustPrice', ''),
                    'take_profit': pos.get('takeProfit', ''),
                    'stop_loss': pos.get('stopLoss', ''),
                    'trailing_stop': pos.get('trailingStop', ''),
                    'created_time': pos.get('createdTime', ''),
                    'updated_time': pos.get('updatedTime', '')
                }

                summary['positions'].append(position_data)
                summary['total_unrealized_pnl'] += position_data['unrealized_pnl']
                summary['total_position_value'] += position_data['position_value']

            return summary

        except Exception as e:
            self.log(f"Error obteniendo resumen de posiciones: {e}")
            return {
                'total_positions': 0,
                'total_unrealized_pnl': 0.0,
                'total_position_value': 0.0,
                'positions': [],
                'error': str(e)
            }
    
    def process_stop_loss_logic(self, position: Dict[str, Any]):
        """Process stop loss logic (preserved from original)"""
        if not self.stop_loss_enabled or float(position['size']) == 0:
            return
            
        try:
            entry_price = float(position['avgPrice'])
            position_value = float(position['positionValue'])
            side = position['side']
            
            # Calculate stop loss price
            percentage = (self.stop_loss_amount * 100) / position_value
            price_change = entry_price * (percentage / 100)
            
            if side == 'Buy':
                stop_price = entry_price - price_change
            else:
                stop_price = entry_price + price_change
                
            if stop_price < 0:
                self.log('Stop loss price below zero - not possible')
                return
                
            # Update stop loss if position changed (value, price, or size)
            position_size = float(position['size'])
            position_key = f"{entry_price}_{position_value}_{position_size}"
            current_key = f"{self.position_price}_{self.position_capital}_{getattr(self, 'position_size', 0)}"

            if position_key != current_key:
                self.log(f'Position changed - updating stop loss to {stop_price}')
                self.log(f'Entry: {entry_price}, Value: {position_value}, Size: {position_size}')
                if self.set_stop_loss(self.symbol, stop_price):
                    self.position_capital = position_value
                    self.position_price = entry_price
                    self.position_size = position_size
                    
        except Exception as e:
            self.log(f"Error en lógica de stop loss: {e}")
    
    def process_take_profit_logic(self, position: Dict[str, Any]):
        """Process take profit logic (preserved from original)"""
        if not self.take_profit_enabled or float(position['avgPrice']) == 0:
            return
            
        try:
            entry_price = float(position['avgPrice'])
            side = position['side']
            qty = float(position['size'])
            
            # Calculate take profit price correctly for each side
            if side == 'Buy':  # Long position - TP above entry price
                tp_price = entry_price + ((entry_price * self.take_profit_percentage) / 100)
            else:  # Short position (Sell) - TP below entry price
                tp_price = entry_price - ((entry_price * self.take_profit_percentage) / 100)

            if tp_price <= 0:
                self.log(f'Take profit price invalid: {tp_price} for {side} position at {entry_price}')
                return

            # Update take profit if position changed (price, size, or value) OR if no TP order exists
            position_key = f"{entry_price}_{qty}"
            current_key = f"{self.position_price}_{getattr(self, 'position_size', 0)}"

            # Force TP placement if no order exists or position changed
            if position_key != current_key or not self.take_profit_order_id:
                self.log(f'🎯 Ejecutando TP: {tp_price} para {side} en {entry_price} ({self.take_profit_percentage}%)')

                # 🔥 CRITICAL: Ensure exclusive TP control for position changes
                self.log(f'Posición cambió - estableciendo TP exclusivo: {tp_price}')

                # Cancel our tracked order first
                if self.take_profit_order_id:
                    self.log(f'Cancelando TP rastreado: {self.take_profit_order_id}')
                    self.cancel_take_profit_order(self.symbol, self.take_profit_order_id)
                    self.take_profit_order_id = ''

                # Ensure no other TP orders exist (manual or external)
                self.cancel_all_tp_orders(self.symbol)
                time.sleep(0.2)  # Brief pause for processing

                # Set new take profit with exclusive control
                self.log(f'Colocando TP exclusivo: {tp_price} para {qty} {side}')
                new_order_id = self.set_take_profit(self.symbol, tp_price, side, qty)
                if new_order_id:
                    self.take_profit_order_id = new_order_id
                    self.position_price = entry_price
                    self.position_size = qty
                    self.log(f'🎯 TP exclusivo establecido - ID: {new_order_id}')
            else:
                # Only log calculation if not executing (reduce spam)
                return
                    
        except Exception as e:
            self.log(f"Error en lógica de take profit: {e}")
    
    def trading_loop(self):
        """Main trading loop"""
        self.log("Bucle de trading iniciado")
        
        while self.running:
            try:
                # Periodic time sync check (every 5 minutes)
                current_time = time.time()
                if current_time - self.last_time_check > 300:  # 5 minutes
                    self.check_time_sync()
                    self.last_time_check = current_time

                if not self.symbol:
                    time.sleep(1)
                    continue

                position = self.get_position_info(self.symbol)
                if not position:
                    time.sleep(1)
                    continue
                
                # Check if position exists
                if float(position['size']) != 0:
                    # Process stop loss logic
                    self.process_stop_loss_logic(position)
                    
                    # Process take profit logic
                    self.process_take_profit_logic(position)
                    
                    # Update status callback if provided
                    if self.status_callback:
                        self.status_callback(position)
                        
                else:
                    # No position - cancel all orders and reset state
                    if self.take_profit_order_id:
                        self.session.cancel_all_orders(category="linear", symbol=self.symbol)
                        self.take_profit_order_id = ''
                    self.position_capital = 0
                    self.position_price = 0
                    
            except Exception as e:
                self.log(f"Error en bucle de trading: {e}")
                time.sleep(5)
                
            time.sleep(1)
        
        self.log("Bucle de trading detenido")
    
    def start_trading(self, symbol: str, stop_loss_enabled: bool = False, 
                     stop_loss_amount: float = 0, take_profit_enabled: bool = False,
                     take_profit_percentage: float = 0) -> bool:
        """Start the trading engine"""
        if self.running:
            self.log("Trading already running")
            return False
            
        if not self.session:
            if not self.initialize_session():
                return False
        
        # Validate symbol format
        if not symbol.upper().endswith('USDT'):
            symbol = symbol.upper() + 'USDT'
            
        self.symbol = symbol
        self.stop_loss_enabled = stop_loss_enabled
        self.stop_loss_amount = stop_loss_amount
        self.take_profit_enabled = take_profit_enabled
        self.take_profit_percentage = take_profit_percentage
        
        # Reset state
        self.position_capital = 0
        self.position_price = 0
        self.take_profit_order_id = ''

        # Check if position exists
        position = self.get_position_info(self.symbol)
        if not position or float(position['size']) == 0:
            self.log(f"No open position found for {self.symbol}")
            return False

        self.log(f"Position found for {self.symbol}")

        # 🔥 CRITICAL: Establish exclusive TP control before starting
        self.log("🚀 Iniciando control exclusivo de Take Profit...")
        if not self.cancel_all_tp_orders(self.symbol):
            self.log("⚠️ Advertencia: No se pudo limpiar completamente las órdenes TP existentes")

        # Wait a moment for cancellations to process
        time.sleep(0.5)

        self.running = True
        self.thread = threading.Thread(target=self.trading_loop, daemon=True)
        self.thread.start()

        return True
    
    def stop_trading(self):
        """Stop the trading engine"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            self.log("Trading detenido")

    def update_sl_amount(self, new_amount: float):
        """Update stop loss amount in real-time"""
        old_amount = self.stop_loss_amount
        self.stop_loss_amount = new_amount
        self.log(f"🛡️ SL actualizado: ${old_amount:.2f} → ${new_amount:.2f} USDT")

        # Update actual SL order if position exists and SL is enabled
        if self.stop_loss_enabled and self.running:
            try:
                position = self.get_position_info(self.symbol)
                if position and float(position['size']) != 0:
                    entry_price = float(position['avgPrice'])
                    side = position['side']

                    # Calculate new SL price using correct logic (same as process_stop_loss_logic)
                    position_value = float(position['positionValue'])
                    percentage = (new_amount * 100) / position_value
                    price_change = entry_price * (percentage / 100)

                    if side == 'Buy':
                        sl_price = entry_price - price_change
                    else:  # Sell
                        sl_price = entry_price + price_change

                    # Force update by clearing existing SL first, then setting new one
                    try:
                        # Clear existing stop loss
                        self.session.set_trading_stop(
                            category="linear",
                            symbol=self.symbol,
                            stopLoss="",
                            positionIdx=self.detect_position_mode(self.symbol)
                        )
                        self.log(f"🧹 SL anterior limpiado")
                    except:
                        pass  # Continue even if clearing fails

                    # Set new stop loss
                    if self.set_stop_loss(self.symbol, sl_price):
                        self.log(f"✅ Orden SL actualizada en Bybit: ${sl_price:.2f}")
                    else:
                        self.log(f"❌ Error actualizando orden SL en Bybit")
            except Exception as e:
                self.log(f"❌ Error actualizando SL en vivo: {e}")

    def update_tp_percentage(self, new_percentage: float):
        """Update take profit percentage in real-time using Limit Orders (lower fees)"""
        old_percentage = self.take_profit_percentage
        self.take_profit_percentage = new_percentage
        self.log(f"💰 TP actualizado: {old_percentage:.2f}% → {new_percentage:.2f}%")

        # Update actual TP order if position exists and TP is enabled
        if self.take_profit_enabled and self.running:
            try:
                position = self.get_position_info(self.symbol)
                if position and float(position['size']) != 0:
                    entry_price = float(position['avgPrice'])
                    side = position['side']
                    full_qty = abs(float(position['size']))

                    # Calculate new TP price
                    if side == 'Buy':  # Long position - TP above entry price
                        tp_price = entry_price + ((entry_price * new_percentage) / 100)
                    else:  # Short position (Sell) - TP below entry price
                        tp_price = entry_price - ((entry_price * new_percentage) / 100)

                    # 🔥 CRITICAL: Ensure exclusive TP control - cancel ALL existing TP orders
                    self.log("🧹 Limpieza completa de TP para actualización exclusiva...")

                    # Cancel our tracked order first
                    if self.take_profit_order_id:
                        self.cancel_take_profit_order(self.symbol, self.take_profit_order_id)
                        self.take_profit_order_id = ''

                    # Cancel ANY other TP orders that might exist (manual or external)
                    self.cancel_all_tp_orders(self.symbol)

                    # Brief pause to ensure cancellations are processed
                    time.sleep(0.2)

                    # Set new take profit using Limit Order (lower maker fees)
                    self.log(f"📊 Colocando nueva orden TP exclusiva para cantidad: {full_qty}")
                    new_order_id = self.set_take_profit(self.symbol, tp_price, side, full_qty)
                    if new_order_id:
                        self.take_profit_order_id = new_order_id
                        self.log(f"✅ Orden TP actualizada en Bybit: ${tp_price:.2f} (Comisión Maker: 0.020%)")
                        self.log(f"🎯 Control exclusivo TP confirmado - ID: {new_order_id}")
                    else:
                        self.log(f"❌ Error actualizando orden TP en Bybit")
            except Exception as e:
                self.log(f"❌ Error actualizando TP en vivo: {e}")

    def update_sl_enabled(self, enabled: bool):
        """Update SL enabled state in real-time"""
        old_state = self.stop_loss_enabled
        self.stop_loss_enabled = enabled
        status = "activado" if enabled else "desactivado"
        self.log(f"🛡️ SL {status} (era: {'activado' if old_state else 'desactivado'})")

        # Apply change immediately if position exists
        if self.running:
            try:
                position = self.get_position_info(self.symbol)
                if position and float(position['size']) != 0:
                    if enabled:
                        # Enable SL - set new stop loss
                        entry_price = float(position['avgPrice'])
                        side = position['side']

                        # Calculate SL price using correct logic (same as process_stop_loss_logic)
                        position_value = float(position['positionValue'])
                        percentage = (self.stop_loss_amount * 100) / position_value
                        price_change = entry_price * (percentage / 100)

                        if side == 'Buy':
                            sl_price = entry_price - price_change
                        else:  # Sell
                            sl_price = entry_price + price_change

                        if self.set_stop_loss(self.symbol, sl_price):
                            self.log(f"✅ SL activado en Bybit: ${sl_price:.2f}")
                    else:
                        # Disable SL - cancel existing stop loss orders
                        try:
                            self.session.cancel_all_orders(
                                category="linear",
                                symbol=self.symbol,
                                orderFilter="StopOrder"
                            )
                            self.log(f"✅ SL desactivado - órdenes canceladas")
                        except Exception as e:
                            self.log(f"⚠️ Error cancelando SL: {e}")
            except Exception as e:
                self.log(f"❌ Error actualizando estado SL: {e}")

    def update_tp_enabled(self, enabled: bool):
        """Update TP enabled state in real-time using Limit Orders (lower fees)"""
        old_state = self.take_profit_enabled
        self.take_profit_enabled = enabled
        status = "activado" if enabled else "desactivado"
        self.log(f"💰 TP {status} (era: {'activado' if old_state else 'desactivado'})")

        # Apply change immediately if position exists
        if self.running:
            try:
                position = self.get_position_info(self.symbol)
                if position and float(position['size']) != 0:
                    if enabled:
                        # 🔥 CRITICAL: Enable TP with exclusive control
                        self.log("🚀 Activando TP con control exclusivo...")

                        # First, ensure no existing TP orders
                        self.cancel_all_tp_orders(self.symbol)
                        time.sleep(0.2)  # Brief pause for processing

                        entry_price = float(position['avgPrice'])
                        side = position['side']
                        qty = abs(float(position['size']))

                        # Calculate TP price correctly for each side
                        if side == 'Buy':  # Long position - TP above entry price
                            tp_price = entry_price + ((entry_price * self.take_profit_percentage) / 100)
                        else:  # Short position (Sell) - TP below entry price
                            tp_price = entry_price - ((entry_price * self.take_profit_percentage) / 100)

                        new_order_id = self.set_take_profit(self.symbol, tp_price, side, qty)
                        if new_order_id:
                            self.take_profit_order_id = new_order_id
                            self.log(f"✅ TP activado en Bybit: ${tp_price:.2f} (Comisión Maker: 0.020%)")
                            self.log(f"🎯 Control exclusivo TP establecido - ID: {new_order_id}")
                    else:
                        # 🔥 CRITICAL: Disable TP with complete cleanup
                        self.log("🧹 Desactivando TP - limpieza completa...")

                        # Cancel our tracked order
                        if self.take_profit_order_id:
                            self.cancel_take_profit_order(self.symbol, self.take_profit_order_id)
                            self.take_profit_order_id = ''

                        # Cancel ANY other TP orders
                        self.cancel_all_tp_orders(self.symbol)
                        self.log(f"✅ TP completamente desactivado - control exclusivo liberado")
            except Exception as e:
                self.log(f"❌ Error actualizando estado TP: {e}")

    def is_running(self) -> bool:
        """Check if trading is running"""
        return self.running
