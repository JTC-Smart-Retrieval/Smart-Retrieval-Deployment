import { useEffect, useState } from "react";
import { QuestionsBankProp, psscocQuestionsBank, eirQuestionsBank } from "@/app/components/ui/autofill-prompt/autofill-prompt.interface";
import { ChatHandler } from "@/app/components/ui/chat/chat.interface";

export default function AutofillQuestion(
  props: Pick<
    ChatHandler,
    "docSelected" | "messages" | "isLoading" | "handleSubmit" | "handleInputChange" | "input"
  >,
) {
  // Keep track of whether to show the overlay
  const [showOverlay, setShowOverlay] = useState(true);
  // Randomly select a subset of questions
  const [randomQuestions, setRandomQuestions] = useState<QuestionsBankProp[]>([]);
  // Keep track of the current question index
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  // Questions bank for PSSCOC or EIR
  const [questionsBank, setQuestionsBank] = useState<QuestionsBankProp[]>(psscocQuestionsBank);

  // Shuffle the array using Fisher-Yates algorithm
  function shuffleArray(array: any[]) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  // TODO: To load the questionsbank from a database in the future

  // Randomly select a subset of 3-4 questions
  useEffect(() => {
    // Select the questions bank based on the document set selected
    if (props.docSelected === "EIR") {
      setQuestionsBank(eirQuestionsBank);
    }
    else {
      setQuestionsBank(psscocQuestionsBank);
    }
    // Shuffle the questionsBank array
    const shuffledQuestions = shuffleArray(questionsBank);
    // Get a random subset of 3-4 questions
    const subsetSize = Math.floor(Math.random() * 2) + 3; // Randomly choose between 3 and 4
    const selectedQuestions = shuffledQuestions.slice(0, subsetSize);
    // Do a short delay before setting the state to show the animation
    setTimeout(() => {
      setRandomQuestions(selectedQuestions);
    }, 300);
  }, [questionsBank, props.docSelected]);


  // Hide overlay when there are messages
  useEffect(() => {
    if (props.messages.length > 0) {
      setShowOverlay(false);
    }
    else {
      setShowOverlay(true);
    }
  }, [props.messages, props.input]);

  // Automatically advance to the next question after a delay
  useEffect(() => {
    const timer = setInterval(() => {
      if (currentQuestionIndex < randomQuestions.length - 1) {
        setCurrentQuestionIndex((prevIndex) => prevIndex + 1);
      }
      else {
        clearInterval(timer); // Stop the timer when all questions have been displayed
      }
    }, 100); // Adjust the delay time as needed (e.g., 5000 milliseconds = 5 seconds)

    return () => clearInterval(timer); // Cleanup the timer on component unmount
  }, [currentQuestionIndex, randomQuestions]);

  // Handle autofill questions click
  const handleAutofillQuestionClick = (questionInput: string) => {
    props.handleInputChange({ target: { name: "message", value: questionInput } } as React.ChangeEvent<HTMLInputElement>);
  };

  return (
    <>
      {showOverlay && (
        <div className="w-full rounded-xl bg-white dark:bg-zinc-700/30 dark:from-inherit p-4 shadow-xl pb-0">
          <div className="rounded-lg pt-5 pr-10 pl-10 flex h-[50vh] flex-col divide-y overflow-y-auto pb-4">
            <h2 className="text-lg text-center font-semibold mb-4">How can I help you with {props.docSelected} today?</h2>
            {randomQuestions.map((question, index) => (
              <ul>
                <li key={index} className={`p-2 mb-2 border border-zinc-500/30 dark:border-white rounded-lg hover:bg-zinc-500/30 transition duration-300 ease-in-out transform cursor-pointer ${index <= currentQuestionIndex ? 'opacity-100 duration-500' : 'opacity-0'}`}>
                  <button
                    className="text-blue-500 w-full text-left"
                    onClick={() => handleAutofillQuestionClick(question.title)}
                  >
                    {question.title}
                  </button>
                </li>
              </ul>
            ))}
          </div>
        </div>
      )}
    </>
  );
}