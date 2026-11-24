# Demo script (~1 minute)

A talk track you can say out loud in an interview. Plain language. Practice it once with the app open on the Inbox tab, with the sample **fi-credit-app** selected and the network guard left on. You do not need to memorize it word for word.

**Setup:** `./run.sh` is already running at [http://127.0.0.1:8518](http://127.0.0.1:8518). If you downloaded the model, leave the backend on **Hybrid**. If you did not, **Rules only** is fine — say that out loud.

---

## The talk track

“When I was in F&I, a credit application never left the desk until we knew who was allowed to see it. Dealer groups have the same instinct with AI: they like the assistant, but those messages cannot just go to a cloud model.

This is a demo of a local triage node for a fictional Lakeside Auto Group. Think of it as a night-shift BDC intern who never leaves the building. I drop in a credit application, and two things happen. First, a set of deterministic checks — the same idea as checking a card with the Luhn digit — finds the SSN, the test Visa, the VIN, the routing number. Those values are masked before the small local model is even allowed to look at the text. Second, the message is classified: this one is F&I, high urgency, route it to the F&I manager.

If I go to Offline proof and try to call Hugging Face, the node refuses the connection, and I can still triage a stranded-car text locally. I want to be honest: this is a demo, not a certified DLP product, and on this box the 1.5B model runs on CPU. In production I'd put this on one GPU, and I'd still keep those checksums next to the model, because I would not let a small LLM be the only thing standing in front of a Social Security number.”

---

## Timing notes

Spoken at a normal pace, that is about 50–60 seconds. If you have a few extra seconds, switch to the **svc-stranded** sample or the Offline proof's stranded-car button and say: “A Civic that won't start on Route 30 is critical, and it goes to the service advisor — the same way a night-shift operator would wake the on-call tech, not log it for Monday.” Then stop and let them ask questions.

If the GGUF is not downloaded, skip the “small local model” sentence and say: “On a laptop with no model file this still runs, in rules-only mode, which is also how the tests and CI run.”

## If they ask a follow-up

- **“Why not just send everything to a hosted model with a BAA?”**  
  “Some groups will, and that can be the right answer. A lot of the ones I sat with in auto retail start from ‘this jacket does not leave the store.’ A local triage node is how I'd meet them there, then negotiate what, if anything, is allowed to go further.”

- **“Will regex catch everything?”**  
  “No, and I say that in the README. A card number split across lines, an SSN written in words, a name with no label — those can slip through. That's why the checks are next to the model, not instead of a real DLP review, and why I would never call this a certified control.”

- **“Why a 1.5B Q4 model on CPU?”**  
  “It's small enough to download for free, run without a GPU, and still follow a tight JSON grammar for category, urgency, and route. I measure the tokens per second and the accuracy on a labeled sample set so I'm not hand-waving. A production node would typically have one GPU, and I might use a larger local model — but I'd keep the same masking step and the same network story.”

- **“What does hybrid actually do?”**  
  “If the rules are confident — a lemon-law letter, a clearly stranded car — they stand, instantly. If two departments both look plausible, like a trade-in with the check engine light on, the local model gets the close call. If the model file isn't there, it falls back to rules. That's also how the unit tests stay green in CI.”

- **“Is the network guard a real air gap?”**  
  “No. It's a user-space socket patch that refuses outbound connections and still allows localhost, so I can demonstrate the idea in a demo. A real air gap is a network control the customer's IT team owns. I would never sell this checkbox as that.”

- **“What would you do on a real dealer group?”**  
  “Sit with compliance and list the fields that must never leave the store. Point this node at their real BDC inbox or DMS notes, not my 40 sample messages. Replace the sidebar toggle with their SSO and their actual routing queues. Keep the checksums, the mask-before-model step, and a scorecard on *their* labeled mail. And be honest about CPU versus one GPU when we talk hardware.”
