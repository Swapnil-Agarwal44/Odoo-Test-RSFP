/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

// this javascript file will work as a medium between the odoo server and the client's python agent, sending the zpl data to the print agent, which will again forward it to the printer using the .bat file

const zplPrintAction = async (env, action) => {
    const zplData = action.params.zpl_data;
    
    try {
        // Send ZPL to the local Python agent running on port 8010
        // Note: 127.0.0.1 refers to the user's OWN computer (localhost)
        const response = await browser.fetch("http://127.0.0.1:8010/print_zpl", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ zpl_data: zplData }),
        });

        if (response.ok) {
            env.services.notification.add("Label sent to printer!", {
                type: "success",
            });
            return { type: "ir.actions.act_window_close" };
        } else {
            const errorData = await response.json();
            env.services.notification.add(`Print Error: ${errorData.message}`, {
                type: "danger",
            });
        }
    } catch (error) {
        console.error(error);
        env.services.notification.add(
            "Could not connect to Local Printer. Is the 'start_printer.bat' script running?", 
            { type: "danger", sticky: true }
        );
    }
};

// Register the action so Python can call it
registry.category("actions").add("custom_rsfp_module.print_zpl_action", zplPrintAction);