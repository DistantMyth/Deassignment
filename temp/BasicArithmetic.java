import java.util.Scanner;

public class BasicArithmetic {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.print("Enter two integers: ");
        int a = sc.nextInt();
        int b = sc.nextInt();

        System.out.println("Sum: " + (a + b));
        System.out.println("Difference: " + (a - b));
        System.out.println("Product: " + (a * b));
        if (b != 0) {
            System.out.println("Quotient: " + (a / b));
        } else {
            System.out.println("Quotient: Undefined (division by zero)");
        }
        sc.close();
    }
}