import { app, HttpRequest, HttpResponseInit } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import { feedbackSchema } from './validator';
import { logger } from '../../shared/logger';

const cosmosConnectionString = process.env['COSMOS_CONNECTION_STRING'];
if (!cosmosConnectionString) {
  throw new Error('Variável de ambiente COSMOS_CONNECTION_STRING não definida');
}

const cosmosClient = new CosmosClient(cosmosConnectionString);
const container = cosmosClient.database('novatech').container('feedbacks');

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  const body = await request.json();
  const parsed = feedbackSchema.safeParse(body);

  if (!parsed.success) {
    logger.warn({ errors: parsed.error.flatten() }, 'Payload de feedback inválido');
    return { status: 400, body: JSON.stringify({ errors: parsed.error.flatten() }) };
  }

  const { queryId, rating, comment, attendantEmail } = parsed.data;

  logger.info({ queryId, rating }, 'Feedback recebido');

  const feedback = {
    queryId,
    rating,
    comment,
    attendantEmail,
    timestamp: new Date().toISOString(),
  };

  try {
    await container.items.create(feedback);
  } catch (err) {
    logger.error({ err, queryId }, 'Erro ao persistir feedback no Cosmos');
    return { status: 500, body: 'Erro interno ao salvar feedback' };
  }

  return { status: 200, body: 'OK' };
}

app.http('feedback', {
  methods: ['POST'],
  handler: feedbackHandler,
});
