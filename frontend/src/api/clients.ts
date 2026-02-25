import { api } from './client'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SeasonalityPeriod {
  name: string
  date_from: string          // MM-DD
  date_to: string            // MM-DD
  avg_occupancy_pct: number | null
  target_markets: string[]   // ISO-2 codes
  booking_channels: string[]
  direct_booking_pct: number | null
}

export interface Hotel {
  id: string
  client_id: string
  name: string
  bb_hotel_id: string | null
  category: string | null
  stars: number | null
  rooms: number | null
  address: string | null
  city: string | null
  country: string | null
  country_code: string | null
  lat: number | null
  lng: number | null
  website_url: string | null
  booking_engine: string | null
  property_type: string | null
  adr: number | null
  seasonality: SeasonalityPeriod[]
  has_scraped_data: boolean
  scraped_at: string | null
  created_at: string
  updated_at: string
}

export interface ClientListItem {
  id: string
  name: string
  bb_client_id: string | null
  agency: string | null
  contact_email: string | null
  hotels_count: number
  created_at: string
  updated_at: string
}

export interface Client extends ClientListItem {
  contact_phone: string | null
  notes: string | null
  owner_id: string
  hotels: Hotel[]
}

export interface HotelCreate {
  name: string
  bb_hotel_id?: string | null
  category?: string
  stars?: number
  address?: string | null
  city?: string | null
  country?: string | null
  country_code?: string | null
  lat?: number | null
  lng?: number | null
  website_url?: string | null
  rooms?: number | null
  booking_engine?: string | null
  property_type?: string | null
  adr?: number | null
  seasonality?: SeasonalityPeriod[]
}

export interface ClientCreate {
  name: string
  bb_client_id?: string | null
  agency?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  notes?: string | null
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const clientsApi = {
  list: () =>
    api.get<ClientListItem[]>('/clients').then((r) => r.data),

  get: (id: string) =>
    api.get<Client>(`/clients/${id}`).then((r) => r.data),

  create: (data: ClientCreate) =>
    api.post<Client>('/clients', data).then((r) => r.data),

  update: (id: string, data: Partial<ClientCreate>) =>
    api.put<Client>(`/clients/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    api.delete<{ detail: string }>(`/clients/${id}`).then((r) => r.data),

  // Hotels
  listHotels: (clientId: string) =>
    api.get<Hotel[]>(`/clients/${clientId}/hotels`).then((r) => r.data),

  createHotel: (clientId: string, data: HotelCreate) =>
    api.post<Hotel>(`/clients/${clientId}/hotels`, data).then((r) => r.data),

  getHotel: (hotelId: string) =>
    api.get<Hotel>(`/clients/hotels/${hotelId}`).then((r) => r.data),

  updateHotel: (hotelId: string, data: Partial<HotelCreate>) =>
    api.put<Hotel>(`/clients/hotels/${hotelId}`, data).then((r) => r.data),

  deleteHotel: (hotelId: string) =>
    api.delete<{ detail: string }>(`/clients/hotels/${hotelId}`).then((r) => r.data),

  getHotelScraped: (hotelId: string) =>
    api.get<{ hotel_id: string; scraped_at: string | null; data: Record<string, unknown> }>(
      `/clients/hotels/${hotelId}/scraped`
    ).then((r) => r.data),

  clearHotelScraped: (hotelId: string) =>
    api.delete<{ detail: string }>(`/clients/hotels/${hotelId}/scraped`).then((r) => r.data),
}
