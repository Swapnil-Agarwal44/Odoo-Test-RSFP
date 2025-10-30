/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";

export class StockMoveLineController extends ListController {
    async setup() {
        await super.setup();
        // Auto-generate lot names for existing records when form opens
        this.autoGenerateLotNames();
    }

    async autoGenerateLotNames() {
        const model = this.model;
        if (model.config.resModel === 'stock.move.line') {
            // Trigger lot name generation for records without lot_name
            const recordsData = model.root.data;
            for (let record of recordsData) {
                if (!record.data.lot_name && record.data.product_id && record.data.state !== 'done') {
                    // Trigger the action to generate missing lot names
                    try {
                        await this.orm.call(
                            'stock.move.line',
                            'action_generate_missing_lot_names',
                            [record.resId]
                        );
                        // Reload the view to show the updated lot name
                        await model.load();
                    } catch (error) {
                        console.log('Could not auto-generate lot name:', error);
                    }
                }
            }
        }
    }
}

registry.category("views").add("stock_move_line_list", {
    ...registry.category("views").get("list"),
    Controller: StockMoveLineController,
});