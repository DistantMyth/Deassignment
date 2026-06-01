import java.util.Scanner;

public class StudentDetails {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.print("Enter name: ");
        String name = sc.nextLine();
        System.out.print("Enter roll number: ");
        int roll = sc.nextInt();
        System.out.print("Enter marks in three subjects: ");
        double m1 = sc.nextDouble();
        double m2 = sc.nextDouble();
        double m3 = sc.nextDouble();

        System.out.println("Student Name: " + name);
        System.out.println("Roll Number: " + roll);
        System.out.println("Marks: " + m1 + ", " + m2 + ", " + m3);
        sc.close();
    }
}