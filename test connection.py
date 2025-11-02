"""
Script di test per verificare la connessione MT5
Esegui questo prima di avviare il server per verificare che MT5 funzioni
"""

import MetaTrader5 as mt5

def test_mt5_connection():
    print("=" * 60)
    print("🧪 TEST CONNESSIONE MT5")
    print("=" * 60)
    
    # Test 1: Inizializzazione
    print("\n1️⃣ Test inizializzazione MT5...")
    if not mt5.initialize():
        print("❌ ERRORE: MT5 non può essere inizializzato!")
        print(f"   Dettagli: {mt5.last_error()}")
        print("\n💡 Soluzioni:")
        print("   - Verifica che MT5 sia installato")
        print("   - Apri MT5 desktop almeno una volta")
        print("   - Controlla che Python sia a 64-bit")
        return False
    
    print("✅ MT5 inizializzato correttamente!")
    
    # Test 2: Versione
    print("\n2️⃣ Versione MT5...")
    version = mt5.version()
    if version:
        print(f"✅ Versione: {version}")
    
    # Test 3: Terminal Info
    print("\n3️⃣ Informazioni terminal...")
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f"✅ Path: {terminal_info.path}")
        print(f"✅ Lingua: {terminal_info.language}")
    
    # Shutdown
    print("\n4️⃣ Chiusura MT5...")
    mt5.shutdown()
    print("✅ MT5 chiuso correttamente!")
    
    print("\n" + "=" * 60)
    print("✅ TUTTI I TEST SUPERATI!")
    print("🚀 Puoi avviare il server con: python server.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        test_mt5_connection()
    except Exception as e:
        print(f"\n❌ ERRORE durante il test: {str(e)}")
        print("\n💡 Assicurati di:")
        print("   1. Aver installato MetaTrader5")
        print("   2. Aver eseguito: pip install MetaTrader5")
        print("   3. Essere su Windows (MT5 non funziona su Linux/Mac)")
