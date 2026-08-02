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

export const sampleVendorInvoices: VendorInvoice[] = [
  {id:"INV-2026-0811",supplier:"Africa Office SARL",dueDate:"2026-08-08",amount:1431000,currency:"XAF",approved:true,bankDetailsComplete:true},
  {id:"INV-2026-0818",supplier:"Horizon Logistics",dueDate:"2026-08-13",amount:2850000,currency:"XAF",approved:true,bankDetailsComplete:true},
  {id:"INV-2026-0820",supplier:"Cameroun Digital",dueDate:"2026-08-16",amount:975000,currency:"XAF",approved:true,bankDetailsComplete:true},
  {id:"INV-2026-0822",supplier:"Bâtiments & Services",dueDate:"2026-08-17",amount:1680000,currency:"XAF",approved:true,bankDetailsComplete:true},
  {id:"INV-2026-0824",supplier:"Transit Central",dueDate:"2026-08-20",amount:720000,currency:"XAF",approved:true,bankDetailsComplete:true},
  {id:"INV-2026-0827",supplier:"Services Plus",dueDate:"2026-08-12",amount:540000,currency:"XAF",approved:false,bankDetailsComplete:true},
  {id:"INV-2026-0829",supplier:"Énergie Conseil",dueDate:"2026-08-15",amount:380000,currency:"XAF",approved:true,paymentHold:true,bankDetailsComplete:true},
  {id:"INV-2026-0831",supplier:"Atlas Maintenance",dueDate:"2026-08-14",amount:610000,currency:"XAF",approved:true,bankDetailsComplete:false},
];

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
