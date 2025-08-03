from agents import Agent, Runner, function_tool, RunContextWrapper, enable_verbose_stdout_logging
from pydantic import BaseModel
from main import config  

enable_verbose_stdout_logging()

# ✅ 1. User Context
# Ye class user ka data rakhti hai — jese unka naam, premium status aur issue type.
class UserContext(BaseModel):
    name: str
    is_premium_user: bool
    issue_type: str = ""

# ✅ 2. Tools with is_enabled logic inside
# Ye tools specialized kaam karte hain jese refund ya service restart — aur andar hi condition check hoti hai.

@function_tool
def refund(wrapper: RunContextWrapper[UserContext]) -> str:
    # Agar user premium nh hai to refund allow nh hoga.
    if not wrapper.context.is_premium_user:
        return "Refund is only available for premium users."
    return f"Refund processed for premium user {wrapper.context.name}."

@function_tool
def restart_service(wrapper: RunContextWrapper[UserContext]) -> str:
    # Sirf jab issue_type 'technical' ho tab hi ye tool chalega.
    if wrapper.context.issue_type != "technical":
        return "Restart service is only available for technical issues."
    return f"Service restarted for user {wrapper.context.name}."

@function_tool
def general_info(_: RunContextWrapper[UserContext]) -> str:
    # Ye general info dene wala tool hai sab users ke liye.
    return "This is general support information. How else can I help?"

# ✅ 3. Agents
# Har agent ek specific maslay ko handle karta hai: billing, technical, general.

billing_agent = Agent[UserContext](
    name="BillingAgent",
    instructions="Only use the refund tool if user is premium.",
    tools=[refund]  # Sirf refund tool use karega
)

technical_agent = Agent[UserContext](
    name="TechnicalAgent",
    instructions="Only use restart_service tool if issue is technical.",
    tools=[restart_service]  # Sirf restart ka tool use karega
)

general_agent = Agent[UserContext](
    name="GeneralAgent",
    instructions="Use general_info tool to answer general queries.",
    tools=[general_info]  # General info wala tool
)

# ✅ 4. Triage Logic
# Ye decide karta hai user ke input ko dekh kar kisko forward karein: billing, technical, ya general agent ko.

def triage(user_input: str, context: UserContext):
    message = user_input.lower()

    if "refund" in message:
        context.issue_type = "billing"
        print("Routing to Billing Agent...")
        result = Runner.run_sync(
            starting_agent=billing_agent,
            input=user_input,
            context=context,
            run_config=config
        )

    elif "restart" in message or "technical" in message:
        context.issue_type = "technical"
        print("Routing to Technical Agent...")
        result = Runner.run_sync(
            starting_agent=technical_agent,
            input=user_input,
            context=context,
            run_config=config
        )

    else:
        context.issue_type = "general"
        print("Routing to General Agent...")
        result = Runner.run_sync(
            starting_agent=general_agent,
            input=user_input,
            context=context,
            run_config=config
        )

    return result.final_output

# ✅ 5. Guardrail
# Ye check karta hai agar user ka input me koi abusive ya forbidden word na ho — warna reject kar deta hai.

def input_guardrail(user_input: str) -> bool:
    banned_words = ["sorry", "apologize", "abuse"]
    return not any(word in user_input.lower() for word in banned_words)

# ✅ 6. CLI Interface
# Ye system user se terminal me baat karta hai — input leta hai aur agents ko forward karta hai.

def main():
    print("Support Agent System Initialized\n")

    name = input("Enter your name: ").strip()
    premium_input = input("Are you a premium user? (yes/no): ").strip().lower()
    is_premium = premium_input == "yes"

    # Context banaya ja raha hai user info ke sath
    context = UserContext(name=name, is_premium_user=is_premium)

    print(f"\nWelcome, {context.name}! How can I assist you? Type your question (type 'exit' to quit):\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if not input_guardrail(user_input):
            print("Input rejected due to banned words.")
            continue

        response = triage(user_input, context)
        print("Response:", response)

# Run the CLI
if __name__ == "__main__":
    main()
