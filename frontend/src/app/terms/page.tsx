import { LegalPage, LegalSection } from '@/components/legal/legal-page';

export default function TermsPage() {
	return (
		<LegalPage title="Terms and risk disclosure">
			<LegalSection title="Analytics, not investment advice">
				<p>
					Latent provides analytical and educational information. It does not execute trades, act as
					a fiduciary, or provide individualized investment, tax, or legal advice. Decisions remain
					the user&apos;s responsibility.
				</p>
			</LegalSection>
			<LegalSection title="Model limitations">
				<p>
					Hidden Markov Model probabilities describe how observations fit an inferred historical
					state. They are not the probability of a future market move. Stress tests are
					sensitivities rather than forecasts, and AI explanations can be incomplete despite being
					grounded in backend facts.
				</p>
			</LegalSection>
			<LegalSection title="Market data">
				<p>
					Market data may be delayed, unavailable, adjusted, or supplied from cached records. Users
					must verify prices and corporate actions with an authoritative source before acting.
				</p>
			</LegalSection>
			<LegalSection title="Availability and acceptable use">
				<p>
					Do not attempt to bypass authentication, ownership checks, request limits, or provider
					usage controls. Service availability is not guaranteed, particularly on free hosting or
					third-party data tiers.
				</p>
			</LegalSection>
			<LegalSection title="Launch requirement">
				<p>
					These product disclosures are an engineering baseline, not jurisdiction-specific legal
					advice. The deploying entity must obtain legal review and insert its governing law,
					liability, termination, and contact terms before public launch.
				</p>
			</LegalSection>
		</LegalPage>
	);
}
