/**
 * Aplicação · Registro central de adaptadores por canal de e-commerce
 */
import { PRIMARY_CHANNEL, QUICKSTORE_CHANNEL } from '@/domain/listings/listingRules.js';
import { mercadoLivreChannel } from './mercadoLivreChannel.js';
import { quickStoreChannel } from './quickStoreChannel.js';

export const CHANNEL_ADAPTERS = {
  [PRIMARY_CHANNEL]: mercadoLivreChannel,
  [QUICKSTORE_CHANNEL]: quickStoreChannel
};

export function getChannelAdapter(slug) {
  return CHANNEL_ADAPTERS[slug] ?? mercadoLivreChannel;
}
