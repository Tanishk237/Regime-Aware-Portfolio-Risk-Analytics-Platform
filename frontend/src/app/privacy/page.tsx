import { LegalPage, LegalSection } from '@/components/legal/legal-page';

export default function PrivacyPage() {
	return (
		<LegalPage title="Privacy notice">
			<LegalSection title="What Latent processes">
				<p>
					Latent processes account details, portfolio trades, generated analytics, saved reports,
					and risk preferences needed to provide the service. Provider API keys entered in the
					browser are held in page memory, sent to the backend for the selected request, and are not
					saved in browser storage or the Latent database. Reloading the page clears them.
				</p>
			</LegalSection>
			<LegalSection title="AI requests">
				<p>
					When you use an AI provider, Latent sends your question, bounded recent questions, and
					selected portfolio facts. Raw CSV files, account details, portfolio names, and notes are
					excluded from this context. Selected financial facts can still be sensitive. The chosen
					provider processes this information under its own policies. The data-readiness check uses
					local application rules and makes no external AI call. Do not include passwords, API keys,
					or other confidential information in chat.
				</p>
			</LegalSection>
			<LegalSection title="Guest sessions">
				<p>
					Guest credentials remain in session storage for the current tab. Guest records are deleted
					on sign-out when reachable and are automatically removed from the backend after the
					configured retention period.
				</p>
			</LegalSection>
			<LegalSection title="Storage and service providers">
				<p>
					Account data is stored in the deployment PostgreSQL database. Market-data and AI requests
					may be sent to the configured external providers. Production operators must name their
					hosting, monitoring, market-data, and AI subprocessors before accepting public users.
				</p>
			</LegalSection>
			<LegalSection title="Your controls">
				<p>
					You can end a guest session, clear browser data, or permanently delete an account and its
					owned portfolio records from Settings. Database backups may retain encrypted copies until
					their configured expiration.
				</p>
			</LegalSection>
			<LegalSection title="Operator contact">
				<p>
					Before launch, replace this section with the deploying entity&apos;s legal name,
					jurisdiction, privacy contact, retention schedule, and applicable data-rights procedure.
				</p>
			</LegalSection>
		</LegalPage>
	);
}
