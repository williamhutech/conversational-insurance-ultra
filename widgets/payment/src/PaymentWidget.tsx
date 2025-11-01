import {
  Badge,
  Button,
  Caption,
  Card,
  Col,
  Divider,
  Row,
  Spacer,
  Text,
  Title,
} from "@openai/apps-sdk"
import WidgetState from "./types"

export default function PaymentWidget() {
  const widgetState = WidgetState.parse(window.openai.widgetState)

  const {
    payment_intent_id,
    checkout_url,
    product_name,
    amount,
    currency,
    status
  } = widgetState

  return (
    <Card size="sm">
      <Col>
        <Row>
          <Caption value="Insurance Checkout" color="secondary" />
          <Spacer />
          <Badge
            label={status}
            color={
              status === "succeeded"
                ? "success"
                : status === "pending"
                  ? "warning"
                  : status === "requires_action"
                    ? "info"
                    : status === "canceled" || status === "failed"
                      ? "danger"
                      : "secondary"
            }
            variant="soft"
            size="sm"
          />
        </Row>
        <Title value={product_name} size="md" />
      </Col>

      <Divider flush />

      <Col>
        <Row>
          <Text value="Amount" size="sm" />
          <Spacer />
          <Text value={`${currency} ${amount}`} size="sm" />
        </Row>
        <Row>
          <Text value="Sales Tax" size="sm" />
          <Spacer />
          <Text value="N.A." size="sm" />
        </Row>
        <Row>
          <Text value="Total Amount" weight="semibold" size="sm" />
          <Spacer />
          <Text value={`${currency} ${amount}`} weight="semibold" size="sm" />
        </Row>
      </Col>

      <Divider flush />

      <Col>
        <Button
          label="Pay via Stripe"
          style="primary"
          iconStart="external-link"
          block
          onClickAction={{
            type: "payment.openCheckout",
            payload: { url: checkout_url, intentId: payment_intent_id },
          }}
        />
        <Text
          value={`Payment ID: ${payment_intent_id}`}
          size="xs"
          color="secondary"
          textAlign="center"
        />
      </Col>
    </Card>
  )
}
