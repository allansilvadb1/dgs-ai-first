import { z } from 'zod';

// number (0..1) oferece granularidade melhor do que enum para confiança do modelo.
export const NovaTechAssistantResponseSchema = z
	.object({
		answer: z.string().trim().min(1, 'answer deve ser uma string nao vazia'),
		source_document: z
			.string()
			.trim()
			.min(3)
			.max(32)
			.regex(
				/^[A-Za-z0-9-]+$/,
				'source_document deve ser um identificador curto (ex: POL-001, PROC-042-v2, SLA-2024, FAQ-Atendimento)'
			)
			.nullable(),
		confidence_score: z
			.number()
			.min(0, 'confidence_score deve estar entre 0 e 1')
			.max(1, 'confidence_score deve estar entre 0 e 1'),
        confidence_level: z
            .enum(['low', 'medium', 'high'])
            .optional(),
	})
	.strict(); // bloqueia campos extras, apenas campos definidos no schema são permitidos

export type NovaTechAssistantResponse = z.infer<
	typeof NovaTechAssistantResponseSchema
>;

// Resposta padrão segura para bloqueios de validação
const DEFAULT_SAFE_RESPONSE: NovaTechAssistantResponse = {
	answer:
		'Não foi possível validar a resposta. Por favor, contate o supervisor.',
	source_document: null,
	confidence_score: 0,
};

/**
 * Valida e aplica guardrails na resposta do assistente.
 *
 * 1. Faz safeParse com NovaTechAssistantResponseSchema.
 * 2. Guardrail: se resposta menciona "carga perigosa" junto com "devolução",
 *    apenas aceita se contiver negativa (ex: "não pode", "não é possível").
 * 3. Em qualquer bloqueio, loga e retorna resposta padrão segura.
 *
 * @param raw - Resposta bruta a validar
 * @returns Resposta validada e autorizada, ou resposta padrão segura
 */
export function validateAndGuard(
	raw: unknown
): NovaTechAssistantResponse {
	// Etapa 1: Validar schema
	const parseResult = NovaTechAssistantResponseSchema.safeParse(raw);

	if (!parseResult.success) {
		const errorMsg = parseResult.error.errors
			.map((e) => `${e.path.join('.')}: ${e.message}`)
			.join('; ');
		console.log(
			`[validateAndGuard] Falha ao parsear resposta: ${errorMsg}`,
			raw
		);
		return DEFAULT_SAFE_RESPONSE;
	}

	const response = parseResult.data;

	// Etapa 2: Aplicar guardrail de "carga perigosa" + "devolução"
	const answerLower = response.answer.toLowerCase();

	// Detectors: carga perigosa (e variações) e devolução (e variações)
	const hasDangerousLoad = /carga\s+perigosa|perigos[ao]/i.test(answerLower);
	const hasRefund = /devolução|devolvê|reembol/i.test(answerLower);

	if (hasDangerousLoad && hasRefund) {
		// Ambos mencionados: verificar se há negativa
		const hasNegation = /não\s+pode|não\s+é\s+possível|não\s+permitido|proibido|vedado/i.test(
			answerLower
		);

		if (!hasNegation) {
			console.log(
				`[validateAndGuard] Bloqueado: resposta menciona "carga perigosa" + "devolução" sem negativa. Answer: "${response.answer}"`
			);
			return DEFAULT_SAFE_RESPONSE;
		}
	}

	// Passou em todos os guardrails
	return response;
}
