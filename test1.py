def get_mean(matrix):
    matrix_one_d = []
    for i in matrix:
        for j in i:
            matrix_one_d.append(matrix[i][j])
    return sum(matrix_one_d)/len(matrix_one_d)

def get_median(matrix):
    n = len(matrix[0])
    if n%2 == 0:
        return (m[n/2 - 1][n-1] + m[n/2][0])/2
    else:
        mid_row = int(n/2) + 1
        return m[mid_row][mid_row]
