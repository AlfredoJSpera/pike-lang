defunc show_menu() %num {
	!!("Select operation:");
	!!("1. Addition (+)");
	!!("2. Subtraction (-)");
	!!("3. Multiplication (*)");
	!!("4. Division (/)");
	!!("5. Exit");
	!("Enter choice (1-5): ");
	&in(choice);
	ret choice;
}

defunc calculate(a: num, b: num, op: num) %num {
	if (op == 1) {
		ret a + b;
	}
	if (op == 2) {
		ret a - b;
	} 
	if (op == 3) {
		ret a * b;
	} 
	if (op == 4) {
		ret a / b;
	}
	
	ret 0;
}

# Main
for (i, 0; 1 == 1; 1) {
	choice := show_menu();
	if (choice == 5) {
		!!("Goodbye!");
		ret;
	}
	if (choice == 0) {
		# Input is a string
		!!("");
		!!("0 or string not valid");
		!!("");
		ret;
	}

	if (choice < 5) {
		if (choice > 0) {
			!("Enter first number: ");
			&in(num1);
			!("Enter second number: ");
			&in(num2);
			
			result := calculate(num1, num2, choice);
			!!("");
			!("Result: ");
			!!(result);
			!!("");
		} else {
			!!("");
			!!("<1 Not valid");
			!!("");
		}
	} else {
		!!("");
		!!(">5 Not valid");
		!!("");
	}
}