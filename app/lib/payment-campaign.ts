export type PaymentPolicy = {
  campaignDays: number[];
  horizonDays: number;
};

export type VendorInvoice = {
  id: string;
  supplier: string;
  dueDate: string;
  amount: number;
  currency: "XAF";
  approved: boolean;
  disputed?: boolean;
  paymentHold?: boolean;
  bankDetailsComplete: boolean;
};

export type CampaignStatus =
  | "scheduled"
  | "sent_to_treasury"
  | "awaiting_controller"
  | "approved";

export const sampleVendorInvoices: VendorInvoice[] = [];

export function addUtcDays(date: Date, days: number) {
  const result = new Date(date);
  result.setUTCDate(result.getUTCDate() + days);
  return result;
}

export function campaignWindow(campaignDate: Date, policy: PaymentPolicy) {
  return {start: campaignDate, end: addUtcDays(campaignDate, policy.horizonDays)};
}

export function isInvoiceEligible(invoice: VendorInvoice, campaignDate: Date, policy: PaymentPolicy) {
  const dueDate = new Date(`${invoice.dueDate}T00:00:00Z`);
  const {end} = campaignWindow(campaignDate, policy);
  return invoice.approved && !invoice.disputed && !invoice.paymentHold && invoice.bankDetailsComplete && dueDate <= end;
}

export function selectCampaignInvoices(invoices: VendorInvoice[], campaignDate: Date, policy: PaymentPolicy) {
  return invoices.filter(invoice => isInvoiceEligible(invoice, campaignDate, policy));
}

export function nextCampaignDate(from: Date, policy: PaymentPolicy) {
  const sortedDays = [...new Set(policy.campaignDays)].filter(day => day >= 1 && day <= 28).sort((a,b) => a-b);
  if (!sortedDays.length) throw new Error("At least one valid campaign day is required");
  for (const day of sortedDays) {
    const candidate = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), day));
    if (candidate >= from) return candidate;
  }
  return new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth()+1, sortedDays[0]));
}
