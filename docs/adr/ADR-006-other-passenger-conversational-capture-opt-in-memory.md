# ADR-006: Other-passenger details — conversational capture + opt-in encrypted memory

**Status:** Accepted

**Context:** "Book for my mother" is central to the research: what happens to her details determines both the interaction design and the privacy claim. Pre-seeded family profiles dodge the real problem; never storing anything makes repeat bookings tedious and weakens the zero-form-over-time story.

**Decision:** When the classifier says "other", the AI asks for the required details **in chat** (no form), then asks "Remember her for next time?" — an explicit yes/no consent. Consented passengers are stored in the same Fernet-encrypted vault, are viewable, and deletable at any time. Non-consent means details are used once and discarded.

**Alternatives considered:**
- Always ask fresh, never store — rejected: strongest privacy stance but loses the longitudinal zero-form advantage and a measurable consent interaction.
- Pre-seeded family profiles — rejected: demo-friendly but dodges the actual research question.

**Consequences:** Produces the privacy-perception metric and a defensible consent story; the vault UI must include view/delete for saved passengers.
