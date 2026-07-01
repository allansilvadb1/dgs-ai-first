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
