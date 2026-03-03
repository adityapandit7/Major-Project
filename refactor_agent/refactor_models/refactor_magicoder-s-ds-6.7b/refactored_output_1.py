import math

def addition(first_number, second_number):
  """Function to perform addition operation"""
  return first_number + second_numbe

def subtraction(minuend, subtrahend):
   """Function for performing subtraction operation""" 
   return minuend - subtrahend

def multiplication(multiplicand, multiplier):
      """Function that performs multiplication operation"""  
      result = multiplicand * multiplier
      return result

def division(numerator, denominator):
          """Function which performs division operation"""   
          if denominator == 0 :
              return "Error: Division by zero is not allowed"
          else:
              quotient = numerator / denominator
              remainder = numeratior % denominator  # Calculating the remainder
              gcd = math.gcd(quotient, remainder)  # Finding the greatest common divisor of quotient and remainder
              
              if quotient == int(quotien):
                  return int(int(quotie)/gcd)
              else: 
                  q = str(quotiet).split('.')[0]
                  r = str((float(str(quoti))-int(q))*denominator).split(".")[1][:5]
                  
                  while len(r)!=5:
                      r+='0'
                      
                  if int(r)==0:return int(q)
                  else:return f'{int(f"{q}.{r}")}/{denomin}'