import { z } from "zod"

const WidgetState = z.strictObject({
  payment_intent_id: z.string(),
  checkout_url: z.string(),
  product_name: z.string(),
  amount: z.string(),
  currency: z.string(),
  status: z.string()
})

export default WidgetState
