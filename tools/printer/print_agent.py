# save this file in any of the permanent locations in the laptop
# also save the start_printer.bat file in the desktop (remember the file should be saved as a .bat file, not .txt file). This file will now work as a start button to activate the TSC TE 244 printer if it's connected to the local system through USB. Just double click the file, and a log terminal will appears. Minimize it (don't close it, the printer will print as long as this terminal box is in process). To close the process, simply use the "ctrl + c" command. A confirmation line will appears, type "y" on the terminal and press enter. The dialog box will close. 

from flask import Flask, request, jsonify
from flask_cors import CORS
import win32print
import logging

app = Flask(__name__)
# Enable CORS to allow Odoo (from a different domain) to talk to this local script
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PRINTER_NAME = "TSC TE244"

@app.route('/print_zpl', methods=['POST'])
def print_zpl():
    try:
        data = request.json
        zpl_code = data.get('zpl_data')
        
        if not zpl_code:
            return jsonify({"status": "error", "message": "No ZPL data provided"}), 400
        
        speed_command = "^XA^PR2,2,2^FS^XZ" 
        final_zpl = speed_command + zpl_code

        # Send to Printer
        hPrinter = win32print.OpenPrinter(PRINTER_NAME)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Odoo_Label", None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            # ZPL must be bytes
            win32print.WritePrinter(hPrinter, final_zpl.encode('utf-8'))
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
            
        logger.info("Label printed successfully")
        return jsonify({"status": "success", "message": "Printed successfully"})
        
    except Exception as e:
        logger.error(f"Print failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print(f"Print Agent running... Listening for Odoo on port 8010")
    # Run on port 8010 to avoid conflicts
    app.run(host='127.0.0.1', port=8010)